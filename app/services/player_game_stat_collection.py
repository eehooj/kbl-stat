"""Collect visible player box-score lines from public completed-game record tabs."""
import json
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import RenderedGameRecordPage, RenderedPage
from app.models import RawSourceDocument, VisibleGameQuarterScore, VisiblePlayerGameStat
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
    two_point_made: int
    three_point_made: int
    three_point_attempted: int
    field_goals_made: int
    field_goals_attempted: int
    rebounds: int
    assists: int
    steals: int
    blocks: int
    dunk_made: int
    free_throw_made: int
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
                "minutes": row.minutes, "points": row.points, "two_point_made": row.two_point_made,
                "field_goals_made": row.field_goals_made, "field_goals_attempted": row.field_goals_attempted,
                "three_point_made": row.three_point_made,
                "three_point_attempted": row.three_point_attempted,
                "rebounds": row.rebounds, "assists": row.assists,
                "steals": row.steals, "blocks": row.blocks, "dunk_made": row.dunk_made,
                "free_throw_made": row.free_throw_made,
                "turnovers": row.turnovers, "fouls": row.fouls,
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


def backfill_visible_dunk_makes(session: Session) -> int:
    """Reparse already preserved public box-score pages after adding the DK field."""
    updated = 0
    documents = session.scalars(select(RawSourceDocument).where(
        RawSourceDocument.source_url.contains("/match/record/"),
    )).all()
    for document in documents:
        try:
            payload = json.loads(document.body)
            visible_text = payload["visible_text"]
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
        if not isinstance(visible_text, str) or "홈 선수기록" not in visible_text:
            continue
        page = RenderedPage(
            url=document.source_url,
            fetched_at=document.fetched_at,
            title=str(payload.get("title", "")),
            visible_text=visible_text,
            content_hash=document.content_hash,
        )
        first_team, second_team = _record_team_names(session, document.source_url, page)
        for row in parse_visible_player_box_scores(page, first_team, second_team):
            stored = session.scalar(select(VisiblePlayerGameStat).where(
                VisiblePlayerGameStat.source_url == document.source_url,
                VisiblePlayerGameStat.team_name == row.team_name,
                VisiblePlayerGameStat.player_name == row.player_name,
            ))
            if stored is not None:
                stored.dunk_made = row.dunk_made
                updated += 1
    session.commit()
    return updated


def backfill_visible_shooting_stats(session: Session) -> int:
    """Reparse preserved visible box-score pages for 3-point and free-throw fields."""
    updated = 0
    documents = session.scalars(select(RawSourceDocument).where(
        RawSourceDocument.source_url.contains("/match/record/"),
    )).all()
    for document in documents:
        try:
            payload = json.loads(document.body)
            visible_text = payload["visible_text"]
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
        if not isinstance(visible_text, str) or "홈 선수기록" not in visible_text:
            continue
        page = RenderedPage(
            url=document.source_url, fetched_at=document.fetched_at,
            title=str(payload.get("title", "")), visible_text=visible_text,
            content_hash=document.content_hash,
        )
        first_team, second_team = _record_team_names(session, document.source_url, page)
        for row in parse_visible_player_box_scores(page, first_team, second_team):
            stored = session.scalar(select(VisiblePlayerGameStat).where(
                VisiblePlayerGameStat.source_url == document.source_url,
                VisiblePlayerGameStat.team_name == row.team_name,
                VisiblePlayerGameStat.player_name == row.player_name,
            ))
            if stored is not None:
                stored.three_point_made = row.three_point_made
                stored.three_point_attempted = row.three_point_attempted
                stored.free_throw_made = row.free_throw_made
                updated += 1
    session.commit()
    return updated


def _record_team_names(
    session: Session, source_url: str, page: RenderedPage,
) -> tuple[str, str]:
    score = session.scalar(select(VisibleGameQuarterScore).where(
        VisibleGameQuarterScore.record_url == source_url,
    ))
    if score is not None:
        return score.first_team_name, score.second_team_name
    provisional = parse_visible_player_box_scores(page, "first", "second")
    resolved: list[str] = []
    for side in ("first", "second"):
        counts: dict[str, int] = {}
        for row in provisional:
            if row.team_name != side:
                continue
            team_names = session.scalars(select(VisiblePlayerGameStat.team_name).where(
                VisiblePlayerGameStat.source_url == source_url,
                VisiblePlayerGameStat.player_name == row.player_name,
            )).all()
            for team_name in set(team_names):
                counts[team_name] = counts.get(team_name, 0) + 1
        if not counts:
            raise ValueError(f"보관된 선수기록에서 팀을 확인할 수 없습니다: {source_url}")
        ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        if len(ordered) > 1 and ordered[0][1] == ordered[1][1]:
            raise ValueError(f"보관된 선수기록의 팀 순서를 확정할 수 없습니다: {source_url}")
        resolved.append(ordered[0][0])
    if resolved[0] == resolved[1]:
        raise ValueError(f"보관된 선수기록의 두 팀이 구분되지 않습니다: {source_url}")
    return resolved[0], resolved[1]


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
                two_point_made=int(values[2]),
                three_point_made=int(values[5]), three_point_attempted=int(values[6]),
                field_goals_made=int(values[8]), field_goals_attempted=int(values[9]),
                free_throw_made=int(values[11]),
                rebounds=int(values[16]), assists=int(values[17]), steals=int(values[18]), blocks=int(values[19]),
                dunk_made=int(values[21]), turnovers=int(values[25]), fouls=int(values[26]),
            ))
        except ValueError as error:
            raise ValueError("경기기록 선수 행의 기본 지표가 숫자가 아닙니다") from error
        index += 3
    return rows
