"""Collect visible player box-score lines from public completed-game record tabs."""
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import RenderedGameRecordPage, RenderedPage
from app.models import VisiblePlayerGameStat
from app.services.game_quarter_collection import (
    _matching_schedule_game,
    parse_visible_quarter_score,
)
from app.services.visible_record_collection import collect_rendered_page

MINUTES = re.compile(r"^\d{1,3}:\d{1,2}$")


@dataclass(frozen=True)
class VisiblePlayerBoxScore:
    team_name: str
    player_name: str
    minutes: str
    points: int
    rebounds: int
    assists: int
    steals: int
    blocks: int
    turnovers: int
    fouls: int


def parse_visible_player_box_scores(
    page: RenderedPage, first_team_name: str, second_team_name: str,
) -> list[VisiblePlayerBoxScore]:
    lines = [line.strip() for line in page.visible_text.splitlines() if line.strip()]
    sections = (("홈 선수기록", first_team_name), ("원정 선수기록", second_team_name))
    parsed: list[VisiblePlayerBoxScore] = []
    for index, (marker, team_name) in enumerate(sections):
        if marker not in lines:
            raise ValueError(f"경기기록 화면에 {marker}이 표시되지 않았습니다")
        start = lines.index(marker) + 2
        end = lines.index(sections[index + 1][0]) if index + 1 < len(sections) else len(lines)
        parsed.extend(_parse_section(lines[start:end], team_name))
    if not parsed:
        raise ValueError("경기기록 화면에 출전 선수 행이 표시되지 않았습니다")
    return parsed


def collect_visible_player_game_stats(session: Session, pages: list[RenderedGameRecordPage]) -> tuple[int, int]:
    saved = unlinked = 0
    for rendered in pages:
        score = parse_visible_quarter_score(rendered.summary_page)
        game = _matching_schedule_game(session, score)
        collect_rendered_page(session, rendered.summary_page, "visible game summary for player box score", commit=False)
        collect_rendered_page(session, rendered.player_page, "visible player game box score", commit=False)
        if game is None:
            unlinked += 1
            continue
        for row in parse_visible_player_box_scores(rendered.player_page, score.first_team_name, score.second_team_name):
            stored = session.scalar(select(VisiblePlayerGameStat).where(
                VisiblePlayerGameStat.schedule_game_id == game.id,
                VisiblePlayerGameStat.team_name == row.team_name,
                VisiblePlayerGameStat.player_name == row.player_name,
            ))
            fields = {
                "minutes": row.minutes, "points": row.points, "rebounds": row.rebounds, "assists": row.assists,
                "steals": row.steals, "blocks": row.blocks, "turnovers": row.turnovers, "fouls": row.fouls,
                "source_url": rendered.player_page.url, "observed_at": rendered.player_page.fetched_at,
            }
            if stored is None:
                session.add(VisiblePlayerGameStat(
                    schedule_game_id=game.id, team_name=row.team_name, player_name=row.player_name, **fields,
                ))
            else:
                for name, value in fields.items():
                    setattr(stored, name, value)
            saved += 1
    session.commit()
    return saved, unlinked


def _parse_section(lines: list[str], team_name: str) -> list[VisiblePlayerBoxScore]:
    rows: list[VisiblePlayerBoxScore] = []
    index = 0
    while index + 2 < len(lines):
        if lines[index] == "계":
            break
        if not lines[index].isdigit():
            index += 1
            continue
        player_name = lines[index + 1]
        values = lines[index + 2].split()
        if values == ["미출전"]:
            index += 3
            continue
        if not values or MINUTES.fullmatch(values[0]) is None or len(values) < 31:
            index += 1
            continue
        try:
            rows.append(VisiblePlayerBoxScore(
                team_name=team_name, player_name=player_name, minutes=values[0], points=int(values[1]),
                rebounds=int(values[16]), assists=int(values[17]), steals=int(values[18]), blocks=int(values[19]),
                turnovers=int(values[25]), fouls=int(values[26]),
            ))
        except ValueError as error:
            raise ValueError("경기기록 선수 행의 기본 지표가 숫자가 아닙니다") from error
        index += 3
    return rows
