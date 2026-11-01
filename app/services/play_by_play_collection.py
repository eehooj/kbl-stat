"""Derive team special scoring from the visibly rendered KBL text broadcast."""
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import RenderedGamePlayByPlay, VisiblePlayByPlayEvent
from app.models import VisibleGameSpecialStat
from app.services.game_quarter_collection import (
    _matching_schedule_game,
    parse_visible_quarter_score,
)
from app.services.visible_record_collection import collect_rendered_page

SCORING = (("3점슛성공", 3), ("2점슛성공", 2), ("덩크슛성공", 2), ("자유투성공", 1))


@dataclass(frozen=True)
class SpecialScoring:
    team_order: int
    bench_points: int
    second_chance_points: int
    starters: tuple[str, ...]


def derive_special_scoring(events: tuple[VisiblePlayByPlayEvent, ...]) -> tuple[SpecialScoring, SpecialScoring]:
    chronological = sorted(events, key=lambda event: (event.quarter, -_clock_seconds(event.clock)))
    starters = {
        side: tuple(_player(event.description, "교체(IN)") for event in chronological
                    if event.quarter == 1 and event.clock == "10:00" and event.team_order == side
                    and "교체(IN)" in event.description) for side in (1, 2)
    }
    if any(len(names) != 5 or len(set(names)) != 5 for names in starters.values()):
        raise ValueError(
            f"1쿼터 10:00 화면에서 팀별 선발 5명을 확정할 수 없습니다: {starters}"
        )
    bench = {1: 0, 2: 0}
    second = {1: 0, 2: 0}
    chance_side: int | None = None
    previous_quarter = 0
    for event in chronological:
        if event.quarter != previous_quarter:
            chance_side = None
            previous_quarter = event.quarter
        description = event.description.strip()
        if "공격리바운드" in description:
            chance_side = event.team_order
            continue
        if chance_side is not None and event.team_order != chance_side and (
            "리바운드" in description
            or "스틸" in description
            or "턴오버" in description
            or _points(description)
        ):
            chance_side = None
        points = _points(description)
        if points:
            player = _player(description, next(label for label, value in SCORING if value == points and label in description))
            if player not in starters[event.team_order]:
                bench[event.team_order] += points
            if chance_side == event.team_order:
                second[event.team_order] += points
            if points in (2, 3):
                chance_side = None
        elif "턴오버" in description and chance_side == event.team_order:
            chance_side = None
    return tuple(SpecialScoring(side, bench[side], second[side], starters[side]) for side in (1, 2))


def collect_visible_special_scoring(session: Session, pages: list[RenderedGamePlayByPlay]) -> tuple[int, int]:
    saved = unlinked = 0
    for rendered in pages:
        score = parse_visible_quarter_score(rendered.summary_page)
        game = _matching_schedule_game(session, score)
        collect_rendered_page(session, rendered.summary_page, "visible game summary for text broadcast", commit=False)
        if game is None:
            unlinked += 1
            continue
        for result, team_name in zip(derive_special_scoring(rendered.events), (score.first_team_name, score.second_team_name)):
            stored = session.scalar(select(VisibleGameSpecialStat).where(
                VisibleGameSpecialStat.schedule_game_id == game.id,
                VisibleGameSpecialStat.team_name == team_name,
            ))
            fields = {
                "bench_points": result.bench_points,
                "second_chance_points": result.second_chance_points,
                "source_url": rendered.summary_page.url,
                "observed_at": rendered.summary_page.fetched_at,
                "calculation_version": "visible-play-by-play-v1",
            }
            if stored is None:
                session.add(VisibleGameSpecialStat(schedule_game_id=game.id, team_name=team_name, **fields))
            else:
                for name, value in fields.items():
                    setattr(stored, name, value)
            saved += 1
    session.commit()
    return saved, unlinked


def _points(description: str) -> int:
    return next((points for label, points in SCORING if label in description), 0)


def _player(description: str, marker: str) -> str:
    return re.sub(r"\s+", " ", description.split(marker, 1)[0]).strip()


def _clock_seconds(clock: str) -> int:
    minutes, seconds = clock.split(":")
    return int(minutes) * 60 + int(seconds)
