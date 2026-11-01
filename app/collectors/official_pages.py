"""Low-frequency collector that reads only KBL pages rendered in a browser."""
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from playwright.sync_api import sync_playwright

from app.config import Settings, get_settings

KBL_BASE_URL = "https://www.kbl.or.kr"
SEASON_LEADER_URL = f"{KBL_BASE_URL}/record/seasonLeader"
MATCH_SCHEDULE_URL = f"{KBL_BASE_URL}/match/schedule"
TEAM_RANKING_URL = f"{KBL_BASE_URL}/match/team-ranking"
DAILY_PICKS_URL = f"{KBL_BASE_URL}/game/challenge/daily-picks"
STATS_KING_URL = f"{KBL_BASE_URL}/game/challenge/stats"
PLAYER_RECORD_URL = f"{KBL_BASE_URL}/record/player"
SCHEDULE_MONTH_HEADER = re.compile(r"(?m)^(?P<year>20\d{2})\s*\.\s*(?P<month>\d{1,2})$")


@dataclass(frozen=True)
class RenderedPage:
    url: str
    fetched_at: datetime
    title: str
    visible_text: str
    content_hash: str

    @property
    def body(self) -> str:
        return json.dumps({"title": self.title, "visible_text": self.visible_text}, ensure_ascii=False)


@dataclass(frozen=True)
class VisiblePlayerRecordRow:
    player_name: str
    team_emblem_code: str
    games_played: int
    points: int
    rebounds: int
    assists: int


@dataclass(frozen=True)
class RenderedPlayerRecordPage:
    page: RenderedPage
    rows: tuple[VisiblePlayerRecordRow, ...]


@dataclass(frozen=True)
class RenderedGameRecordPage:
    summary_page: RenderedPage
    player_page: RenderedPage


@dataclass(frozen=True)
class VisiblePlayByPlayEvent:
    quarter: int
    clock: str
    team_order: int
    description: str


@dataclass(frozen=True)
class RenderedGamePlayByPlay:
    summary_page: RenderedPage
    events: tuple[VisiblePlayByPlayEvent, ...]


@dataclass(frozen=True)
class RenderedDailyPicksResultPage:
    page: RenderedPage
    correct_option_labels: tuple[str, ...]


class KBLRenderedPageClient:
    """Reads visible text only; it never requests KBL's internal API endpoints."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def render(self, url: str) -> RenderedPage:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=self.settings.kbl_browser_channel, headless=True)
            page = browser.new_page(locale="ko-KR")
            page.goto(url, wait_until="domcontentloaded", timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
            page.wait_for_timeout(1500)
            visible_text = page.locator("body").inner_text()
            title = page.title()
            final_url = page.url
            browser.close()
        return RenderedPage(
            url=final_url, fetched_at=datetime.now(UTC), title=title, visible_text=visible_text,
            content_hash=sha256(visible_text.encode("utf-8")).hexdigest(),
        )

    def render_season_leaders(self) -> RenderedPage:
        return self.render(SEASON_LEADER_URL)

    def render_match_schedule(self) -> RenderedPage:
        return self.render(MATCH_SCHEDULE_URL)

    def render_current_schedule_record_summaries(self, limit: int) -> list[RenderedPage]:
        """Open a bounded number of visible schedule-card record links, without forms or APIs."""
        if limit < 1:
            raise ValueError("limit must be positive")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=self.settings.kbl_browser_channel, headless=True)
            page = browser.new_page(locale="ko-KR")
            page.goto(MATCH_SCHEDULE_URL, wait_until="domcontentloaded", timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
            page.wait_for_timeout(1500)
            button_offset = 2  # The first two exact '기록' labels are navigation, not game-card buttons.
            available = page.get_by_text("기록", exact=True).count() - button_offset
            rendered: list[RenderedPage] = []
            for index in range(min(limit, max(available, 0))):
                page.get_by_text("기록", exact=True).nth(button_offset + index).click()
                page.wait_for_url(re.compile(r".*/match/record/.*"), timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
                page.wait_for_timeout(500)
                rendered.append(_make_rendered_page(page.url, page.title(), page.locator("body").inner_text()))
                page.go_back(wait_until="domcontentloaded", timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
                page.wait_for_timeout(500)
            browser.close()
        return rendered

    def render_current_schedule_player_records(self, limit: int) -> list[RenderedGameRecordPage]:
        """Open a bounded number of public box-score tabs from visible completed schedule cards."""
        if limit < 1:
            raise ValueError("limit must be positive")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=self.settings.kbl_browser_channel, headless=True)
            page = browser.new_page(locale="ko-KR")
            page.goto(MATCH_SCHEDULE_URL, wait_until="domcontentloaded", timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
            page.wait_for_timeout(1500)
            button_offset = 2
            available = page.get_by_text("기록", exact=True).count() - button_offset
            rendered: list[RenderedGameRecordPage] = []
            for index in range(min(limit, max(available, 0))):
                # Opening "경기기록" changes the record page in place.  Going back once
                # therefore returns to the summary tab, not the schedule.  Start every
                # iteration from the public schedule so every requested game is visited.
                if index:
                    page.goto(
                        MATCH_SCHEDULE_URL,
                        wait_until="domcontentloaded",
                        timeout=int(self.settings.kbl_http_timeout_seconds * 1000),
                    )
                    page.wait_for_timeout(700)
                page.get_by_text("기록", exact=True).nth(button_offset + index).click()
                page.wait_for_url(re.compile(r".*/match/record/.*"), timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
                page.wait_for_timeout(500)
                summary = _make_rendered_page(page.url, page.title(), page.locator("body").inner_text())
                page.get_by_text("경기기록", exact=True).click()
                page.wait_for_timeout(500)
                player_page = _make_rendered_page(page.url, page.title(), page.locator("body").inner_text())
                rendered.append(RenderedGameRecordPage(summary_page=summary, player_page=player_page))
            browser.close()
        return rendered

    def render_current_schedule_play_by_play(self, limit: int) -> list[RenderedGamePlayByPlay]:
        """Read the four visible text-broadcast quarter tabs for completed schedule games."""
        if limit < 1:
            raise ValueError("limit must be positive")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=self.settings.kbl_browser_channel, headless=True)
            page = browser.new_page(locale="ko-KR")
            rendered: list[RenderedGamePlayByPlay] = []
            for index in range(limit):
                page.goto(MATCH_SCHEDULE_URL, wait_until="domcontentloaded", timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
                page.wait_for_timeout(700 if index else 1500)
                buttons = page.get_by_text("기록", exact=True)
                if index >= buttons.count() - 2:
                    break
                buttons.nth(2 + index).click()
                page.wait_for_url(re.compile(r".*/match/record/.*"), timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
                page.wait_for_timeout(500)
                summary = _make_rendered_page(page.url, page.title(), page.locator("body").inner_text())
                text_broadcast = page.get_by_text("문자중계", exact=True)
                if text_broadcast.count() != 1:
                    continue
                text_broadcast.click()
                page.wait_for_timeout(500)
                try:
                    periods = _visible_play_by_play_periods(page)
                except ValueError:
                    # A schedule card can expose a record link before the broadcast tabs are ready.
                    continue
                events: list[VisiblePlayByPlayEvent] = []
                for label, quarter in periods:
                    page.get_by_text(label, exact=True).click()
                    page.wait_for_timeout(300)
                    tables = page.get_by_role("table", name="문자 중계")
                    if tables.count() != 1:
                        raise ValueError("문자중계 표가 화면에 하나만 표시되지 않았습니다")
                    events.extend(_visible_play_by_play_rows(tables, quarter))
                rendered.append(RenderedGamePlayByPlay(summary, tuple(events)))
            browser.close()
        return rendered

    def render_game_play_by_play(self, record_url: str) -> RenderedGamePlayByPlay:
        """Render one known public record URL and read its visible quarter tabs."""
        if not record_url.startswith(f"{KBL_BASE_URL}/match/record/"):
            raise ValueError("record_url must be a public KBL match record URL")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=self.settings.kbl_browser_channel, headless=True)
            page = browser.new_page(locale="ko-KR")
            page.goto(record_url, wait_until="domcontentloaded", timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
            page.wait_for_timeout(1500)
            summary = _make_rendered_page(page.url, page.title(), page.locator("body").inner_text())
            page.get_by_text("문자중계", exact=True).click()
            page.wait_for_timeout(500)
            events: list[VisiblePlayByPlayEvent] = []
            for label, quarter in _visible_play_by_play_periods(page):
                page.get_by_text(label, exact=True).click()
                page.wait_for_timeout(300)
                table = page.get_by_role("table", name="문자 중계")
                if table.count() != 1:
                    raise ValueError("문자중계 표가 화면에 하나만 표시되지 않았습니다")
                events.extend(_visible_play_by_play_rows(table, quarter))
            browser.close()
        return RenderedGamePlayByPlay(summary, tuple(events))

    def render_team_rankings(self) -> RenderedPage:
        return self.render(TEAM_RANKING_URL)

    def render_daily_picks(self) -> RenderedPage:
        return self.render(DAILY_PICKS_URL)

    def render_daily_picks_history(self, days: int) -> list[RenderedDailyPicksResultPage]:
        """Navigate visible previous-day controls and read displayed correct option states."""
        if days < 1:
            raise ValueError("days must be positive")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=self.settings.kbl_browser_channel, headless=True)
            page = browser.new_page(locale="ko-KR")
            page.goto(DAILY_PICKS_URL, wait_until="domcontentloaded", timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
            page.wait_for_timeout(1500)
            rendered: list[RenderedDailyPicksResultPage] = []
            for _ in range(days):
                page.get_by_role("button", name="이전으로").click()
                page.wait_for_timeout(700)
                visible_text = _daily_picks_question_text(page.locator("body").inner_text())
                correct_labels = _visible_daily_picks_correct_options(page)
                rendered.append(RenderedDailyPicksResultPage(
                    page=_make_rendered_page(page.url, page.title(), visible_text),
                    correct_option_labels=tuple(correct_labels),
                ))
            browser.close()
        return rendered

    def render_stats_king(self) -> RenderedPage:
        return self.render(STATS_KING_URL)

    def render_registered_roster(self) -> RenderedPage:
        from app.services.registered_roster import MARKER, ROSTER_URL

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=self.settings.kbl_browser_channel, headless=True)
            page = browser.new_page(locale="ko-KR")
            page.goto(ROSTER_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            navigation = page.locator("select").last
            count = navigation.locator("option").count()
            if not count:
                raise ValueError("등록선수 페이지 탐색 미표시")
            seen = set()
            rows = []
            for number in range(1, count + 1):
                navigation.select_option(str(number))
                page.wait_for_timeout(700)
                current = []
                for row in page.locator("table tbody tr").all():
                    cells = row.locator("td").all_inner_texts()
                    if len(cells) == 8:
                        current.append((cells[0].strip(), cells[1].strip()))
                if not current or any(pair in seen for pair in current):
                    raise ValueError("등록선수 페이지 누락 또는 중복")
                seen.update(current)
                rows.extend("\t".join(pair) for pair in current)
            result = _make_rendered_page(ROSTER_URL, page.title(), MARKER + "\n".join(rows))
            browser.close()
            return result

    def render_player_records(self) -> list[RenderedPlayerRecordPage]:
        """Render every visible page of the public player season-record table."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=self.settings.kbl_browser_channel, headless=True)
            page = browser.new_page(locale="ko-KR")
            page.goto(PLAYER_RECORD_URL, wait_until="domcontentloaded", timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
            page.wait_for_timeout(1500)
            page_selector = "div.page.desktop select"
            page_count = page.locator(f"{page_selector} option").count()
            if page_count == 0:
                browser.close()
                raise ValueError("KBL player-record screen did not display page navigation")
            rendered_pages: list[RenderedPlayerRecordPage] = []
            for number in range(1, page_count + 1):
                page.locator(page_selector).select_option(str(number))
                page.wait_for_timeout(700)
                visible_text = page.locator("body").inner_text()
                rendered_pages.append(RenderedPlayerRecordPage(
                    page=_make_rendered_page(page.url, page.title(), visible_text),
                    rows=tuple(_visible_player_record_rows(page)),
                ))
            browser.close()
        return rendered_pages

    def render_schedule_season(self, season: str) -> list[RenderedPage]:
        """Navigate KBL's visible schedule calendar for October through May."""
        start_year, end_year = _parse_season(season)
        months = [(start_year, month) for month in range(10, 13)] + [(end_year, month) for month in range(1, 6)]
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=self.settings.kbl_browser_channel, headless=True)
            page = browser.new_page(locale="ko-KR")
            page.goto(MATCH_SCHEDULE_URL, wait_until="domcontentloaded", timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
            page.wait_for_timeout(1500)
            current = _rendered_month(page.locator("body").inner_text())
            target = months[0]
            direction = "다음으로" if current < target else "이전으로"
            for _ in range(24):
                if current == target:
                    break
                page.get_by_role("button", name=direction).click()
                page.wait_for_timeout(700)
                updated = _rendered_month(page.locator("body").inner_text())
                if updated == current:
                    raise RuntimeError("KBL schedule month did not change after navigation")
                current = updated
            else:
                raise RuntimeError("KBL schedule could not reach the requested season")

            pages: list[RenderedPage] = []
            for index, expected in enumerate(months):
                visible_text = page.locator("body").inner_text()
                if _rendered_month(visible_text) != expected:
                    raise RuntimeError("KBL schedule displayed an unexpected month")
                pages.append(_make_rendered_page(page.url, page.title(), visible_text))
                if index < len(months) - 1:
                    page.get_by_role("button", name="다음으로").click()
                    page.wait_for_timeout(700)
            browser.close()
        return pages


def _parse_season(season: str) -> tuple[int, int]:
    match = re.fullmatch(r"(20\d{2})-(20\d{2})", season)
    if match is None or int(match[2]) != int(match[1]) + 1:
        raise ValueError("Season must use YYYY-YYYY and span one year")
    return int(match[1]), int(match[2])


def _rendered_month(visible_text: str) -> tuple[int, int]:
    match = SCHEDULE_MONTH_HEADER.search(visible_text)
    if match is None:
        raise ValueError("Rendered schedule did not display a year/month header")
    return int(match["year"]), int(match["month"])


def _make_rendered_page(url: str, title: str, visible_text: str) -> RenderedPage:
    return RenderedPage(
        url=url, fetched_at=datetime.now(UTC), title=title, visible_text=visible_text,
        content_hash=sha256(visible_text.encode("utf-8")).hexdigest(),
    )


def _visible_player_record_rows(page) -> list[VisiblePlayerRecordRow]:
    rows: list[VisiblePlayerRecordRow] = []
    for row in page.locator("tbody tr").all():
        cells = row.locator("td").all_inner_texts()
        emblem = row.locator("td.name i")
        player = row.locator("td.name p")
        if len(cells) < 23 or emblem.count() != 1 or player.count() != 1:
            continue
        team_class = emblem.get_attribute("class") or ""
        team_codes = [item for item in team_class.split() if item != "ic-emblem"]
        if len(team_codes) != 1:
            raise ValueError("KBL player-record row did not display one team emblem code")
        try:
            rows.append(VisiblePlayerRecordRow(
                player_name=player.inner_text().strip(),
                team_emblem_code=team_codes[0],
                games_played=int(cells[2]),
                points=int(cells[6]),
                rebounds=int(cells[21]),
                assists=int(cells[22]),
            ))
        except ValueError as error:
            raise ValueError("KBL player-record row contained non-integer base statistics") from error
    if not rows:
        raise ValueError("KBL player-record screen did not display player rows")
    return rows


def _visible_play_by_play_rows(table, quarter: int) -> list[VisiblePlayByPlayEvent]:
    events: list[VisiblePlayByPlayEvent] = []
    for row in table.locator("tr").all():
        cells = [cell.strip() for cell in row.locator("th, td").all_inner_texts()]
        clock_index = next((i for i, value in enumerate(cells) if MINUTE_CLOCK.fullmatch(value)), None)
        if clock_index is None:
            continue
        if clock_index > 0 and cells[clock_index - 1]:
            events.append(VisiblePlayByPlayEvent(quarter, cells[clock_index], 1, cells[clock_index - 1]))
        if clock_index + 1 < len(cells) and cells[clock_index + 1]:
            events.append(VisiblePlayByPlayEvent(quarter, cells[clock_index], 2, cells[clock_index + 1]))
    return events


MINUTE_CLOCK = re.compile(r"\d{1,2}:\d{2}")


def _visible_play_by_play_periods(page) -> list[tuple[str, int]]:
    """Return regulation and overtime tabs exactly as displayed on the broadcast screen."""
    periods: list[tuple[str, int]] = []
    for label in page.locator(".view-tab label").all_inner_texts():
        normalized = label.strip()
        regulation = re.fullmatch(r"Q([1-4])", normalized)
        overtime = re.fullmatch(r"EQ(\d+)", normalized)
        if regulation:
            periods.append((normalized, int(regulation[1])))
        elif overtime:
            periods.append((normalized, 4 + int(overtime[1])))
    if [period for _label, period in periods[:4]] != [1, 2, 3, 4]:
        raise ValueError("문자중계 화면에서 Q1~Q4 탭을 확인할 수 없습니다")
    return periods


def _visible_daily_picks_correct_options(page) -> list[str]:
    groups: dict[str, str] = {}
    inputs = page.locator("input[type=radio][name^=radio]").all()
    for item in inputs:
        classes = set((item.get_attribute("class") or "").split())
        if "true" not in classes:
            continue
        name = item.get_attribute("name") or ""
        option_id = item.get_attribute("id") or ""
        if not name or not option_id or name in groups:
            raise ValueError("Daily Picks 과거 화면의 정답 상태를 하나로 확정할 수 없습니다")
        label = page.locator(f'label[for="{option_id}"]')
        if label.count() != 1:
            raise ValueError("Daily Picks 정답 선택지 라벨이 화면에 하나만 표시되지 않았습니다")
        groups[name] = label.inner_text().strip()
    return [groups[name] for name in sorted(groups, key=lambda value: int(value.removeprefix("radio")))]


def _daily_picks_question_text(visible_text: str) -> str:
    """Exclude the unrelated masked winner list from retained question evidence."""
    lines = visible_text.splitlines()
    winner_index = next((index for index, line in enumerate(lines) if line.strip() == "정답자"), None)
    return visible_text if winner_index is None else "\n".join(lines[:winner_index]).strip()
