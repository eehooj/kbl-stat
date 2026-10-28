"""Persist only standings values visibly rendered on KBL's team-ranking page."""
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import RenderedPage
from app.models import Season, TeamSeasonStanding
from app.services.visible_record_collection import collect_rendered_page

SEASON = re.compile(r"20\d{2}-20\d{2}")
RECORD = re.compile(r"^\d+\s*-\s*\d+$")
STREAK = re.compile(r"^\d+[승패]$")
HEAD_TO_HEAD = re.compile(r"^\d+승\d+패$")
TABLE_HEADER = ("순위", "팀", "승", "패", "승률", "승차", "최근 5경기", "연속", "홈", "원정", "다음경기", "상대전적")


@dataclass(frozen=True)
class VisibleTeamStanding:
    team_name: str
    rank: int
    wins: int
    losses: int
    win_rate: float
    games_back: float
    recent_five: str
    streak: str
    home_record: str
    away_record: str
    next_opponent_name: str
    head_to_head: str


def parse_visible_team_rankings(visible_text: str) -> tuple[str, list[VisibleTeamStanding]]:
    seasons = SEASON.findall(visible_text)
    if not seasons:
        raise ValueError("Rendered team-ranking page did not display a season label")
    lines = [
        cell.strip()
        for line in visible_text.splitlines()
        for cell in line.split("\t")
        if cell.strip()
    ]
    header_index = _find_table_header(lines)
    rows: list[VisibleTeamStanding] = []
    index = header_index + len(TABLE_HEADER)
    while index + 11 < len(lines):
        values = lines[index:index + 12]
        if not _is_standing_row(values):
            if rows:
                break
            index += 1
            continue
        rows.append(VisibleTeamStanding(
            rank=int(values[0]), team_name=values[1], wins=int(values[2]), losses=int(values[3]),
            win_rate=float(values[4]), games_back=float(values[5]), recent_five=values[6], streak=values[7],
            home_record=values[8], away_record=values[9], next_opponent_name=values[10], head_to_head=values[11],
        ))
        index += 12
    if not rows:
        raise ValueError("Rendered team-ranking page had no parseable standing rows")
    return seasons[0], rows


def _find_table_header(lines: list[str]) -> int:
    for index in range(len(lines) - len(TABLE_HEADER) + 1):
        if tuple(lines[index:index + len(TABLE_HEADER)]) == TABLE_HEADER:
            return index
    raise ValueError("Rendered team-ranking page did not display the regular-season table header")


def _is_standing_row(values: list[str]) -> bool:
    return (
        values[0].isdigit() and values[2].isdigit() and values[3].isdigit()
        and _is_number(values[4]) and _is_number(values[5])
        and bool(values[6]) and STREAK.fullmatch(values[7]) is not None
        and RECORD.fullmatch(values[8]) is not None and RECORD.fullmatch(values[9]) is not None
        and HEAD_TO_HEAD.fullmatch(values[11]) is not None
    )


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def collect_visible_team_rankings(session: Session, page: RenderedPage) -> int:
    season_name, standings = parse_visible_team_rankings(page.visible_text)
    season = session.scalar(select(Season).where(Season.name == season_name))
    if season is None:
        season = Season(code=season_name, name=season_name)
        session.add(season)
        session.flush()
    collect_rendered_page(session, page, f"visible team standings={len(standings)}", commit=False)
    for standing in standings:
        record = session.scalar(select(TeamSeasonStanding).where(
            TeamSeasonStanding.season_id == season.id,
            TeamSeasonStanding.team_name == standing.team_name,
        ))
        fields = {
            "rank": standing.rank, "wins": standing.wins, "losses": standing.losses,
            "win_rate": standing.win_rate, "games_back": standing.games_back,
            "recent_five": standing.recent_five, "streak": standing.streak,
            "home_record": standing.home_record, "away_record": standing.away_record,
            "next_opponent_name": standing.next_opponent_name, "head_to_head": standing.head_to_head,
            "source_url": page.url, "observed_at": page.fetched_at,
        }
        if record is None:
            session.add(TeamSeasonStanding(season_id=season.id, team_name=standing.team_name, **fields))
        else:
            for name, value in fields.items():
                setattr(record, name, value)
    session.commit()
    return len(standings)
