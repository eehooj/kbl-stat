"""Parse only game facts that are visibly rendered by KBL's schedule page."""
import re
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import RenderedPage
from app.models import Season, VisibleScheduleGame
from app.services.visible_record_collection import collect_rendered_page

KST = ZoneInfo("Asia/Seoul")
MONTH_HEADER = re.compile(r"^(?P<year>20\d{2})\s*\.\s*(?P<month>\d{1,2})$")
DAY_HEADER = re.compile(r"^(?P<month>\d{1,2})\.(?P<day>\d{2})$")
TIME = re.compile(r"^\d{1,2}:\d{2}$")
TEAM_SCORE = re.compile(r"^(?P<team>.+?)\s+(?P<score>\d+)$")
COMPETITIONS = {"정규시즌", "플레이오프", "올스타게임", "컵대회", "D리그", "OPEN MATCH DAY", "EASL"}
FINAL_ACTIONS = {"기록", "하이라이트"}


@dataclass(frozen=True)
class VisibleScheduleFixture:
    starts_at: datetime
    competition: str
    venue: str
    first_team_name: str
    second_team_name: str
    first_score: int | None
    second_score: int | None
    status: str


def _season_name(starts_at: datetime) -> str:
    return f"{starts_at.year}-{starts_at.year + 1}" if starts_at.month >= 10 else f"{starts_at.year - 1}-{starts_at.year}"


def parse_visible_schedule(visible_text: str) -> list[VisibleScheduleFixture]:
    """Read schedule cards without turning their first/second team order into home/away."""
    lines = [line.strip() for line in visible_text.splitlines() if line.strip()]
    year = month = None
    for line in lines:
        header = MONTH_HEADER.match(line)
        if header:
            year, month = int(header["year"]), int(header["month"])
            break
    if year is None or month is None:
        raise ValueError("Rendered schedule did not display a year/month header")

    fixtures: list[VisibleScheduleFixture] = []
    index = 0
    day: int | None = None
    while index < len(lines):
        day_match = DAY_HEADER.match(lines[index])
        if day_match and int(day_match["month"]) == month:
            day = int(day_match["day"])
            index += 1
            continue
        if day is None or lines[index] not in COMPETITIONS:
            index += 1
            continue
        competition = lines[index]
        if index + 4 >= len(lines) or not TIME.match(lines[index + 1]):
            index += 1
            continue
        first = TEAM_SCORE.match(lines[index + 3])
        second = TEAM_SCORE.match(lines[index + 4])
        if first is not None and second is not None:
            first_team_name, first_score = first["team"], int(first["score"])
            second_team_name, second_score = second["team"], int(second["score"])
            cursor = index + 5
        elif index + 6 < len(lines) and lines[index + 4].isdigit() and lines[index + 6].isdigit():
            first_team_name, first_score = lines[index + 3], int(lines[index + 4])
            second_team_name, second_score = lines[index + 5], int(lines[index + 6])
            cursor = index + 7
        else:
            index += 1
            continue
        actions: list[str] = []
        while cursor < len(lines):
            if DAY_HEADER.match(lines[cursor]) or lines[cursor] in COMPETITIONS:
                break
            actions.append(lines[cursor])
            cursor += 1
        completed = any(action in FINAL_ACTIONS for action in actions)
        fixtures.append(VisibleScheduleFixture(
            starts_at=datetime(year, month, day, *map(int, lines[index + 1].split(":")), tzinfo=KST),
            competition=competition,
            venue=lines[index + 2],
            first_team_name=first_team_name, second_team_name=second_team_name,
            first_score=first_score if completed else None,
            second_score=second_score if completed else None,
            status="final" if completed else "scheduled",
        ))
        index = cursor
    if not fixtures:
        raise ValueError("Rendered schedule had no parseable game cards")
    return fixtures


def _observed_key(fixture: VisibleScheduleFixture) -> str:
    rendered = (
        f"{fixture.starts_at.isoformat()}|{fixture.competition}|{fixture.venue}|"
        f"{fixture.first_team_name}|{fixture.second_team_name}"
    )
    return sha256(rendered.encode("utf-8")).hexdigest()


def collect_visible_schedule(session: Session, page: RenderedPage) -> int:
    fixtures = parse_visible_schedule(page.visible_text)
    collect_rendered_page(session, page, f"visible schedule games={len(fixtures)}", commit=False)
    for fixture in fixtures:
        season_name = _season_name(fixture.starts_at)
        season = session.scalar(select(Season).where(Season.name == season_name))
        if season is None:
            season = Season(code=season_name, name=season_name)
            session.add(season)
            session.flush()
        observed_key = _observed_key(fixture)
        game = session.scalar(select(VisibleScheduleGame).where(VisibleScheduleGame.observed_key == observed_key))
        fields = {
            "season_id": season.id, "starts_at": fixture.starts_at, "competition": fixture.competition,
            "venue": fixture.venue, "first_team_name": fixture.first_team_name,
            "second_team_name": fixture.second_team_name, "first_score": fixture.first_score,
            "second_score": fixture.second_score, "status": fixture.status, "source_url": page.url,
            "observed_at": page.fetched_at,
        }
        if game is None:
            session.add(VisibleScheduleGame(observed_key=observed_key, **fields))
        else:
            for name, value in fields.items():
                setattr(game, name, value)
    session.commit()
    return len(fixtures)


def collect_visible_schedule_pages(session: Session, pages: list[RenderedPage]) -> tuple[int, int]:
    """Collect a season's rendered pages, retaining empty month evidence too."""
    collected_games = 0
    empty_pages = 0
    for page in pages:
        try:
            collected_games += collect_visible_schedule(session, page)
        except ValueError as error:
            if str(error) != "Rendered schedule had no parseable game cards":
                raise
            collect_rendered_page(session, page, "visible schedule games=0")
            empty_pages += 1
    return collected_games, empty_pages
