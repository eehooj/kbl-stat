"""Classify visible Daily Picks prompts and link them to matching visible schedule cards."""
import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ChallengeOption,
    ChallengeQuestion,
    ChallengeType,
    DailyPicksScheduleLink,
    VisibleScheduleGame,
)

MATCHING_METHOD = "same-start-venue-two-option-team-label-containment-v1"
METRICS = {
    "필드골 성공률": "field_goal_pct",
    "세컨드 찬스에 의한 득점": "second_chance_points",
    "벤치 득점": "bench_points",
    "덩크슛": "dunk_made",
    "2점슛 성공": "two_point_made",
    "득점": "points",
    "리바운드": "rebounds",
    "어시스트": "assists",
    "스틸": "steals",
    "블록": "blocks",
    "턴오버": "turnovers",
    "파울": "fouls",
}
QUARTER = re.compile(r"(?P<quarter>[1-4])\s*쿼터")


def classify_visible_daily_pick(question_text: str) -> dict[str, object]:
    """Return only literal metric and period hints that occur in the visible question text."""
    metric = next((value for label, value in METRICS.items() if label in question_text), None)
    quarter = QUARTER.search(question_text)
    return {
        "metric": metric,
        "quarter": int(quarter["quarter"]) if quarter else None,
        "classification_status": "classified" if metric else "unclassified",
    }


def link_daily_picks_schedule_games(session: Session) -> int:
    questions = list(session.scalars(select(ChallengeQuestion).where(
        ChallengeQuestion.challenge_type == ChallengeType.DAILY_PICKS,
    )))
    games = list(session.scalars(select(VisibleScheduleGame)))
    linked = 0
    for question in questions:
        payload = question.raw_payload if isinstance(question.raw_payload, dict) else {}
        classification = classify_visible_daily_pick(question.text or "")
        if payload.get("classification") != classification:
            question.raw_payload = {**payload, "classification": classification}
        game = _find_match(question, payload, games, session)
        if game is None:
            continue
        link = session.scalar(select(DailyPicksScheduleLink).where(DailyPicksScheduleLink.question_id == question.id))
        if link is None:
            session.add(DailyPicksScheduleLink(
                question_id=question.id, schedule_game_id=game.id,
                matching_method=MATCHING_METHOD, linked_at=datetime.now(UTC),
            ))
            linked += 1
    session.commit()
    return linked


def _find_match(
    question: ChallengeQuestion, payload: dict[str, object], games: list[VisibleScheduleGame], session: Session,
) -> VisibleScheduleGame | None:
    if question.question_date is None or not isinstance(payload.get("venue"), str):
        return None
    option_labels = list(session.scalars(select(ChallengeOption.label).where(ChallengeOption.question_id == question.id)))
    matches = [
        game for game in games
        if _same_local_time(question.question_date, game.starts_at)
        and _normalized(payload["venue"]) == _normalized(game.venue)
        and _option_teams_match(option_labels, game)
    ]
    return matches[0] if len(matches) == 1 else None


def _option_teams_match(option_labels: list[str], game: VisibleScheduleGame) -> bool:
    return all(
        any(_labels_equivalent(option, team_name) for option in option_labels)
        for team_name in (game.first_team_name, game.second_team_name)
    )


def _labels_equivalent(first: str, second: str) -> bool:
    first_normalized, second_normalized = _normalized(first), _normalized(second)
    return first_normalized in second_normalized or second_normalized in first_normalized


def _normalized(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def _same_local_time(first: datetime, second: datetime) -> bool:
    return first.replace(tzinfo=None) == second.replace(tzinfo=None)
