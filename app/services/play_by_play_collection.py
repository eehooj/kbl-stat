"""Derive team special scoring from the visibly rendered KBL text broadcast."""
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import RenderedGamePlayByPlay, VisiblePlayByPlayEvent
from app.models import VisibleGameSpecialStat, VisiblePlayerGameStat
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
    good_defense: int
    scoring_lead_seconds: int
    play_by_play_points: int
    starters: tuple[str, ...]


def derive_special_scoring(events: tuple[VisiblePlayByPlayEvent, ...]) -> tuple[SpecialScoring, SpecialScoring]:
    indexed_events = enumerate(events)
    chronological = [
        event for _index, event in sorted(
            indexed_events,
            key=lambda item: (
                item[1].quarter,
                -_clock_seconds(item[1].clock),
                -item[0],
            ),
        )
    ]
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
    good_defense = {1: 0, 2: 0}
    lead_seconds, play_by_play_points = _derive_scoring_lead(events)
    chance_side: int | None = None
    previous_quarter = 0
    for event in chronological:
        if event.quarter != previous_quarter:
            chance_side = None
            previous_quarter = event.quarter
        description = event.description.strip()
        if description.endswith(" 굿디펜스"):
            good_defense[event.team_order] += 1
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
    return tuple(
        SpecialScoring(
            side, bench[side], second[side], good_defense[side],
            lead_seconds[side], play_by_play_points[side], starters[side],
        )
        for side in (1, 2)
    )


def collect_visible_special_scoring(session: Session, pages: list[RenderedGamePlayByPlay]) -> tuple[int, int]:
    saved = unlinked = 0
    for rendered in pages:
        score = parse_visible_quarter_score(rendered.summary_page)
        game = _matching_schedule_game(session, score)
        collect_rendered_page(session, rendered.summary_page, "visible game summary for text broadcast", commit=False)
        if game is None:
            unlinked += 1
            continue
        results = derive_special_scoring(rendered.events)
        teams = (
            (results[0], score.first_team_name, score.first_total),
            (results[1], score.second_team_name, score.second_total),
        )
        for result, team_name, team_total in teams:
            if result.play_by_play_points != team_total:
                raise ValueError(
                    f"문자중계 득점 합계가 공식 경기 합계와 다릅니다: "
                    f"{team_name} {result.play_by_play_points} != {team_total}"
                )
            _verify_bench_points(session, game.id, team_name, team_total, result)
            stored = session.scalar(select(VisibleGameSpecialStat).where(
                VisibleGameSpecialStat.schedule_game_id == game.id,
                VisibleGameSpecialStat.team_name == team_name,
            ))
            fields = {
                "bench_points": result.bench_points,
                "second_chance_points": result.second_chance_points,
                "good_defense": result.good_defense,
                "scoring_lead_seconds": result.scoring_lead_seconds,
                "source_url": rendered.summary_page.url,
                "observed_at": rendered.summary_page.fetched_at,
                "calculation_version": "visible-play-by-play-v4",
            }
            if stored is None:
                session.add(VisibleGameSpecialStat(schedule_game_id=game.id, team_name=team_name, **fields))
            else:
                for name, value in fields.items():
                    setattr(stored, name, value)
            saved += 1
    session.commit()
    return saved, unlinked


def _verify_bench_points(
    session: Session,
    schedule_game_id: int,
    team_name: str,
    team_total: int,
    result: SpecialScoring,
) -> None:
    """Fail closed when a complete visible box score contradicts the text broadcast."""
    rows = list(session.scalars(select(VisiblePlayerGameStat).where(
        VisiblePlayerGameStat.schedule_game_id == schedule_game_id,
        VisiblePlayerGameStat.team_name == team_name,
    )))
    if not rows or sum(row.points for row in rows) != team_total:
        return
    starter_names = {_normalized_name(name) for name in result.starters}
    box_score_bench = sum(
        row.points for row in rows if _normalized_name(row.player_name) not in starter_names
    )
    if box_score_bench != result.bench_points:
        raise ValueError(
            f"문자중계 벤치 득점이 공식 선수기록 합계와 다릅니다: "
            f"{team_name} {result.bench_points} != {box_score_bench}"
        )


def _points(description: str) -> int:
    return next((points for label, points in SCORING if label in description), 0)


def _derive_scoring_lead(
    events: tuple[VisiblePlayByPlayEvent, ...],
) -> tuple[dict[int, int], dict[int, int]]:
    """Replay visible made-shot rows and assign each interval to the team leading then."""
    scores = {1: 0, 2: 0}
    lead_seconds = {1: 0, 2: 0}
    scoring_by_period: dict[int, list[VisiblePlayByPlayEvent]] = {}
    for index, event in sorted(
        enumerate(events),
        key=lambda item: (item[1].quarter, -_clock_seconds(item[1].clock), -item[0]),
    ):
        if _points(event.description):
            scoring_by_period.setdefault(event.quarter, []).append(event)
    for quarter in range(1, max(4, max((event.quarter for event in events), default=4)) + 1):
        previous_clock = 600 if quarter <= 4 else 300
        for event in scoring_by_period.get(quarter, []):
            current_clock = _clock_seconds(event.clock)
            leader = 1 if scores[1] > scores[2] else 2 if scores[2] > scores[1] else None
            if leader is not None:
                lead_seconds[leader] += previous_clock - current_clock
            scores[event.team_order] += _points(event.description)
            previous_clock = current_clock
        leader = 1 if scores[1] > scores[2] else 2 if scores[2] > scores[1] else None
        if leader is not None:
            lead_seconds[leader] += previous_clock
    return lead_seconds, scores


def _player(description: str, marker: str) -> str:
    return re.sub(r"\s+", " ", description.split(marker, 1)[0]).strip()


def _clock_seconds(clock: str) -> int:
    minutes, seconds = clock.split(":")
    return int(minutes) * 60 + int(seconds)


def _normalized_name(name: str) -> str:
    return re.sub(r"\s+", "", name).casefold()
