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

    def render_team_rankings(self) -> RenderedPage:
        return self.render(TEAM_RANKING_URL)

    def render_daily_picks(self) -> RenderedPage:
        return self.render(DAILY_PICKS_URL)

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
