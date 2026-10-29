"""Recommend Daily Picks from prior visible team box-score totals only."""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ChallengeOption,
    ChallengeQuestion,
    ChallengeType,
    DailyPicksScheduleLink,
    VisiblePlayerGameStat,
    VisibleScheduleGame,
)
from app.services.daily_picks_schedule_linking import classify_visible_daily_pick

METRIC_LABELS = {
    "steals": "스틸",
    "two_point_made": "2점슛 성공",
    "turnovers": "턴오버",
    "blocks": "블록슛",
    "fouls": "개인 파울",
}


@dataclass(frozen=True)
class DailyPicksRecommendation:
    question_text: str
    metric: str | None
    recommended_team: str | None
    first_average: float | None
    second_average: float | None
    games_used: int
    status: str


def recommend_daily_picks(session: Session) -> list[DailyPicksRecommendation]:
    questions = list(session.scalars(select(ChallengeQuestion).where(
        ChallengeQuestion.challenge_type == ChallengeType.DAILY_PICKS,
    ).order_by(ChallengeQuestion.question_date.desc())))
    if not questions:
        return []
    target_date = questions[0].question_date
    questions = [question for question in questions if question.question_date == target_date]
    recommendations: list[DailyPicksRecommendation] = []
    for question in sorted(questions, key=lambda item: (item.raw_payload or {}).get("ordinal", 0)):
        link = session.scalar(select(DailyPicksScheduleLink).where(DailyPicksScheduleLink.question_id == question.id))
        if link is None:
            recommendations.append(DailyPicksRecommendation(question.text or "", None, None, None, None, 0, "일정 미연결"))
            continue
        game = session.get(VisibleScheduleGame, link.schedule_game_id)
        payload = question.raw_payload if isinstance(question.raw_payload, dict) else {}
        metric = (payload.get("classification") or classify_visible_daily_pick(question.text or "")).get("metric")
        if game is None or not isinstance(metric, str) or metric not in METRIC_LABELS:
            recommendations.append(DailyPicksRecommendation(question.text or "", None, None, None, None, 0, "질문 지표 미확인"))
            continue
        averages = _recent_team_averages(session, game, metric)
        first = averages.get(game.first_team_name)
        second = averages.get(game.second_team_name)
        if first is None or second is None or min(first[0], second[0]) < 3:
            recommendations.append(DailyPicksRecommendation(question.text or "", metric, None, None, None, 0, "최근 기록 부족"))
            continue
        winner = game.first_team_name if first[1] > second[1] else game.second_team_name if second[1] > first[1] else None
        option_labels = list(session.scalars(select(ChallengeOption.label).where(ChallengeOption.question_id == question.id)))
        recommendations.append(DailyPicksRecommendation(
            question.text or "", metric, _matching_option(winner, option_labels), first[1], second[1], min(first[0], second[0]),
            "추천 가능" if winner else "평균 동률",
        ))
    return recommendations


def render_daily_picks_recommendations(items: list[DailyPicksRecommendation]) -> str:
    if not items:
        return "KBL DAILY PICKS PREDICTION\n\n확인된 Daily Picks 문제가 없습니다."
    lines = ["KBL DAILY PICKS PREDICTION"]
    for index, item in enumerate(items, start=1):
        if item.recommended_team is None:
            lines.append(f"Pick {index}: 추천 보류 - {item.status} ({item.question_text})")
        else:
            lines.append(
                f"Pick {index}: {item.recommended_team} - {METRIC_LABELS[item.metric or '']} 최근 {item.games_used}경기 "
                f"{item.first_average:.2f} vs {item.second_average:.2f}"
            )
    return "\n".join(lines)


def _recent_team_averages(
    session: Session, target: VisibleScheduleGame, metric: str,
) -> dict[str, tuple[int, float]]:
    rows = session.execute(
        select(VisiblePlayerGameStat, VisibleScheduleGame)
        .join(VisibleScheduleGame, VisibleScheduleGame.id == VisiblePlayerGameStat.schedule_game_id)
        .where(VisibleScheduleGame.starts_at < target.starts_at)
        .order_by(VisibleScheduleGame.starts_at.desc())
    ).all()
    totals: dict[str, dict[int, int]] = {target.first_team_name: {}, target.second_team_name: {}}
    for stat, game in rows:
        target_team = next((team for team in totals if _same_team(team, stat.team_name)), None)
        value = getattr(stat, metric)
        if target_team is not None and value is not None and len(totals[target_team]) < 5:
            totals[target_team][game.id] = totals[target_team].get(game.id, 0) + value
    return {
        team: (len(games), sum(games.values()) / len(games))
        for team, games in totals.items() if games
    }


def _matching_option(team_name: str | None, options: list[str]) -> str | None:
    return next((option for option in options if team_name is not None and _same_team(option, team_name)), None)


def _same_team(first: str, second: str) -> bool:
    first_normalized, second_normalized = "".join(first.split()).casefold(), "".join(second.split()).casefold()
    return first_normalized in second_normalized or second_normalized in first_normalized
