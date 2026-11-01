"""Recommend Daily Picks from prior visible team box-score totals only."""
from collections.abc import Sized
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ChallengeOption,
    ChallengeQuestion,
    ChallengeResult,
    ChallengeType,
    DailyPicksScheduleLink,
    VisibleGameSpecialStat,
    VisiblePlayerGameStat,
    VisibleScheduleGame,
)
from app.services.daily_picks_schedule_linking import classify_visible_daily_pick

METRIC_LABELS = {
    "field_goal_pct": "필드골 성공률",
    "three_point_pct": "3점슛 성공률",
    "free_throw_made": "자유투 성공",
    "rebounds": "리바운드",
    "steals": "스틸",
    "two_point_made": "2점슛 성공",
    "turnovers": "턴오버",
    "blocks": "블록슛",
    "dunk_made": "덩크슛 성공",
    "fouls": "개인 파울",
    "bench_points": "벤치 득점",
    "second_chance_points": "세컨드 찬스 득점",
    "good_defense": "굿디펜스",
    "scoring_lead_seconds": "득점 우위시간",
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


@dataclass(frozen=True)
class DailyPicksBacktest:
    answered: int
    evaluable: int
    correct: int
    accuracy: float | None
    skipped: dict[str, int]


@dataclass(frozen=True)
class DailyPicksLookbackEvaluation:
    game_limit: int | None
    evaluable: int
    correct: int
    accuracy: float | None


@dataclass(frozen=True)
class DailyPicksStrategyEvaluation:
    strategy: str
    evaluable: int
    correct: int
    accuracy: float | None


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
        recommendations.append(_recommend_question(session, question))
    return recommendations


def backtest_daily_picks(session: Session, game_limit: int | None = 5) -> DailyPicksBacktest:
    rows = session.execute(
        select(ChallengeQuestion, ChallengeResult)
        .join(ChallengeResult, ChallengeResult.question_id == ChallengeQuestion.id)
        .where(ChallengeQuestion.challenge_type == ChallengeType.DAILY_PICKS)
        .order_by(ChallengeQuestion.question_date)
    ).all()
    correct = evaluable = 0
    skipped: dict[str, int] = {}
    for question, result in rows:
        recommendation = _recommend_question(session, question, game_limit=game_limit)
        answer = result.official_answer if isinstance(result.official_answer, dict) else {}
        answer_label = answer.get("label")
        if recommendation.recommended_team is None or not isinstance(answer_label, str):
            skipped[recommendation.status] = skipped.get(recommendation.status, 0) + 1
            continue
        evaluable += 1
        if _same_team(recommendation.recommended_team, answer_label):
            correct += 1
    return DailyPicksBacktest(
        answered=len(rows), evaluable=evaluable, correct=correct,
        accuracy=(correct / evaluable) if evaluable else None, skipped=skipped,
    )


def evaluate_daily_picks_lookbacks(
    session: Session, limits: tuple[int | None, ...] = (3, 5, 10, None),
) -> list[DailyPicksLookbackEvaluation]:
    evaluations: list[DailyPicksLookbackEvaluation] = []
    for limit in limits:
        result = backtest_daily_picks(session, game_limit=limit)
        evaluations.append(DailyPicksLookbackEvaluation(
            game_limit=limit, evaluable=result.evaluable, correct=result.correct, accuracy=result.accuracy,
        ))
    return evaluations


def render_daily_picks_lookback_evaluations(items: list[DailyPicksLookbackEvaluation]) -> str:
    lines = ["KBL DAILY PICKS LOOKBACK EVALUATION"]
    for item in items:
        label = "전체 이전 경기" if item.game_limit is None else f"최근 {item.game_limit}경기"
        accuracy = "평가 불가" if item.accuracy is None else f"{item.accuracy * 100:.1f}%"
        lines.append(f"{label}: 평가 {item.evaluable}건 / 적중 {item.correct}건 / {accuracy}")
    return "\n".join(lines)


def evaluate_daily_picks_strategies(
    session: Session, since: date | None = None,
) -> list[DailyPicksStrategyEvaluation]:
    evaluations: list[DailyPicksStrategyEvaluation] = []
    for strategy, opponent_adjusted in (("팀 자체 평균", False), ("상대 허용 50% 결합", True)):
        result = _backtest_daily_picks_strategy(session, opponent_adjusted, since)
        evaluations.append(DailyPicksStrategyEvaluation(
            strategy=strategy, evaluable=result.evaluable, correct=result.correct, accuracy=result.accuracy,
        ))
    return evaluations


def render_daily_picks_strategy_evaluations(items: list[DailyPicksStrategyEvaluation]) -> str:
    lines = ["KBL DAILY PICKS STRATEGY EVALUATION"]
    for item in items:
        accuracy = "평가 불가" if item.accuracy is None else f"{item.accuracy * 100:.1f}%"
        lines.append(f"{item.strategy}: 평가 {item.evaluable}건 / 적중 {item.correct}건 / {accuracy}")
    return "\n".join(lines)


def _backtest_daily_picks_strategy(
    session: Session, opponent_adjusted: bool, since: date | None = None,
) -> DailyPicksBacktest:
    rows = session.execute(
        select(ChallengeQuestion, ChallengeResult)
        .join(ChallengeResult, ChallengeResult.question_id == ChallengeQuestion.id)
        .where(ChallengeQuestion.challenge_type == ChallengeType.DAILY_PICKS)
        .order_by(ChallengeQuestion.question_date)
    ).all()
    if since is not None:
        rows = [(question, result) for question, result in rows
                if question.question_date is not None and question.question_date.date() >= since]
    correct = evaluable = 0
    skipped: dict[str, int] = {}
    for question, result in rows:
        recommendation = _recommend_question(session, question, opponent_adjusted=opponent_adjusted)
        answer = result.official_answer if isinstance(result.official_answer, dict) else {}
        answer_label = answer.get("label")
        if recommendation.recommended_team is None or not isinstance(answer_label, str):
            skipped[recommendation.status] = skipped.get(recommendation.status, 0) + 1
            continue
        evaluable += 1
        if _same_team(recommendation.recommended_team, answer_label):
            correct += 1
    return DailyPicksBacktest(
        answered=len(rows), evaluable=evaluable, correct=correct,
        accuracy=(correct / evaluable) if evaluable else None, skipped=skipped,
    )


def render_daily_picks_backtest(result: DailyPicksBacktest) -> str:
    accuracy = "평가 불가" if result.accuracy is None else f"{result.accuracy * 100:.1f}%"
    lines = [
        "KBL DAILY PICKS BACKTEST",
        (
            f"공식 정답 {result.answered}건 / 평가 가능 {result.evaluable}건 / "
            f"적중 {result.correct}건 / 적중률 {accuracy}"
        ),
    ]
    if result.skipped:
        lines.append("평가 제외: " + ", ".join(f"{key} {value}건" for key, value in sorted(result.skipped.items())))
    return "\n".join(lines)


def _recommend_question(
    session: Session, question: ChallengeQuestion, game_limit: int | None = 5,
    opponent_adjusted: bool = False,
) -> DailyPicksRecommendation:
    link = session.scalar(select(DailyPicksScheduleLink).where(
        DailyPicksScheduleLink.question_id == question.id,
    ))
    if link is None:
        return DailyPicksRecommendation(question.text or "", None, None, None, None, 0, "일정 미연결")
    game = session.get(VisibleScheduleGame, link.schedule_game_id)
    metric = classify_visible_daily_pick(question.text or "").get("metric")
    if game is None or not isinstance(metric, str) or metric not in METRIC_LABELS:
        return DailyPicksRecommendation(question.text or "", None, None, None, None, 0, "질문 지표 미확인")
    if opponent_adjusted:
        averages = _opponent_adjusted_averages(session, game, metric, game_limit)
    elif metric == "field_goal_pct":
        averages = _recent_field_goal_percentages(session, game, game_limit)
    elif metric == "three_point_pct":
        averages = _recent_three_point_percentages(session, game, game_limit)
    elif metric in {"bench_points", "second_chance_points", "good_defense", "scoring_lead_seconds"}:
        averages = _recent_special_scoring_averages(session, game, metric, game_limit)
    else:
        averages = _recent_team_averages(session, game, metric, game_limit)
    first = averages.get(game.first_team_name)
    second = averages.get(game.second_team_name)
    if first is None or second is None or min(first[0], second[0]) < 3:
        return DailyPicksRecommendation(question.text or "", metric, None, None, None, 0, "최근 기록 부족")
    winner = game.first_team_name if first[1] > second[1] else game.second_team_name if second[1] > first[1] else None
    option_labels = list(session.scalars(select(ChallengeOption.label).where(
        ChallengeOption.question_id == question.id,
    )))
    return DailyPicksRecommendation(
        question.text or "", metric, _matching_option(winner, option_labels),
        first[1], second[1], min(first[0], second[0]), "추천 가능" if winner else "평균 동률",
    )


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
    session: Session, target: VisibleScheduleGame, metric: str, game_limit: int | None = 5,
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
        if target_team is not None and value is not None and (
            game.id in totals[target_team] or _has_room(totals[target_team], game_limit)
        ):
            totals[target_team][game.id] = totals[target_team].get(game.id, 0) + value
    return {
        team: (len(games), sum(games.values()) / len(games))
        for team, games in totals.items() if games
    }


def _recent_field_goal_percentages(
    session: Session, target: VisibleScheduleGame, game_limit: int | None = 5,
) -> dict[str, tuple[int, float]]:
    return _recent_shooting_percentages(
        session, target, "field_goals_made", "field_goals_attempted", game_limit,
    )


def _recent_three_point_percentages(
    session: Session, target: VisibleScheduleGame, game_limit: int | None = 5,
) -> dict[str, tuple[int, float]]:
    return _recent_shooting_percentages(
        session, target, "three_point_made", "three_point_attempted", game_limit,
    )


def _recent_shooting_percentages(
    session: Session, target: VisibleScheduleGame, made_field: str, attempted_field: str,
    game_limit: int | None = 5,
) -> dict[str, tuple[int, float]]:
    rows = session.execute(
        select(VisiblePlayerGameStat, VisibleScheduleGame)
        .join(VisibleScheduleGame, VisibleScheduleGame.id == VisiblePlayerGameStat.schedule_game_id)
        .where(VisibleScheduleGame.starts_at < target.starts_at)
        .order_by(VisibleScheduleGame.starts_at.desc())
    ).all()
    totals: dict[str, dict[int, list[int]]] = {target.first_team_name: {}, target.second_team_name: {}}
    for stat, game in rows:
        target_team = next((team for team in totals if _same_team(team, stat.team_name)), None)
        made = getattr(stat, made_field)
        attempted = getattr(stat, attempted_field)
        if target_team is None or made is None or attempted is None:
            continue
        if game.id in totals[target_team] or _has_room(totals[target_team], game_limit):
            game_totals = totals[target_team].setdefault(game.id, [0, 0])
            game_totals[0] += made
            game_totals[1] += attempted
    return {
        team: (len(games), (sum(item[0] for item in games.values()) / sum(item[1] for item in games.values())) * 100)
        for team, games in totals.items() if games and sum(item[1] for item in games.values()) > 0
    }


def _recent_special_scoring_averages(
    session: Session, target: VisibleScheduleGame, metric: str, game_limit: int | None = 5,
) -> dict[str, tuple[int, float]]:
    rows = session.execute(
        select(VisibleGameSpecialStat, VisibleScheduleGame)
        .join(VisibleScheduleGame, VisibleScheduleGame.id == VisibleGameSpecialStat.schedule_game_id)
        .where(VisibleScheduleGame.starts_at < target.starts_at)
        .order_by(VisibleScheduleGame.starts_at.desc())
    ).all()
    values: dict[str, list[int]] = {target.first_team_name: [], target.second_team_name: []}
    for stat, _game in rows:
        target_team = next((team for team in values if _same_team(team, stat.team_name)), None)
        value = getattr(stat, metric)
        if target_team is not None and value is not None and _has_room(values[target_team], game_limit):
            values[target_team].append(value)
    return {
        team: (len(items), sum(items) / len(items))
        for team, items in values.items() if items
    }


def _has_room(items: Sized, game_limit: int | None) -> bool:
    return game_limit is None or len(items) < game_limit


def _opponent_adjusted_averages(
    session: Session, target: VisibleScheduleGame, metric: str, game_limit: int | None,
) -> dict[str, tuple[int, float]]:
    made_attempted = None
    if metric in {"bench_points", "second_chance_points", "good_defense", "scoring_lead_seconds"}:
        rows = session.execute(
            select(VisibleGameSpecialStat, VisibleScheduleGame)
            .join(VisibleScheduleGame, VisibleScheduleGame.id == VisibleGameSpecialStat.schedule_game_id)
            .where(VisibleScheduleGame.starts_at < target.starts_at)
            .order_by(VisibleScheduleGame.starts_at.desc())
        ).all()
        game_values: dict[int, dict[str, float]] = {}
        games: dict[int, VisibleScheduleGame] = {}
        for stat, game in rows:
            value = getattr(stat, metric)
            if value is not None:
                games.setdefault(game.id, game)
                game_values.setdefault(game.id, {})[stat.team_name] = float(value)
    else:
        made_attempted = {
            "field_goal_pct": ("field_goals_made", "field_goals_attempted"),
            "three_point_pct": ("three_point_made", "three_point_attempted"),
        }.get(metric)
        rows = session.execute(
            select(VisiblePlayerGameStat, VisibleScheduleGame)
            .join(VisibleScheduleGame, VisibleScheduleGame.id == VisiblePlayerGameStat.schedule_game_id)
            .where(VisibleScheduleGame.starts_at < target.starts_at)
            .order_by(VisibleScheduleGame.starts_at.desc())
        ).all()
        games = {}
        raw: dict[int, dict[str, list[float]]] = {}
        for stat, game in rows:
            if made_attempted:
                made, attempted = getattr(stat, made_attempted[0]), getattr(stat, made_attempted[1])
                if made is None or attempted is None:
                    continue
                values = (float(made), float(attempted))
            else:
                value = getattr(stat, metric)
                if value is None:
                    continue
                values = (float(value), 0.0)
            games.setdefault(game.id, game)
            totals = raw.setdefault(game.id, {}).setdefault(stat.team_name, [0.0, 0.0])
            totals[0] += values[0]
            totals[1] += values[1]
        game_values = {
            game_id: {
                team: (values[0] / values[1] * 100 if made_attempted and values[1] else values[0])
                for team, values in teams.items() if not made_attempted or values[1]
            }
            for game_id, teams in raw.items()
        }
    target_teams = (target.first_team_name, target.second_team_name)
    production: dict[str, list[float]] = {team: [] for team in target_teams}
    allowed: dict[str, list[float]] = {team: [] for team in target_teams}
    production_shots = {team: [0.0, 0.0] for team in target_teams}
    allowed_shots = {team: [0.0, 0.0] for team in target_teams}
    for team in target_teams:
        for game_id, game in games.items():
            participants = (game.first_team_name, game.second_team_name)
            side = next((name for name in participants if _same_team(team, name)), None)
            if side is None:
                continue
            opponent = participants[1] if side == participants[0] else participants[0]
            own_key = next((name for name in game_values.get(game_id, {}) if _same_team(name, side)), None)
            opponent_key = next((name for name in game_values.get(game_id, {}) if _same_team(name, opponent)), None)
            if own_key is None or opponent_key is None:
                continue
            production[team].append(game_values[game_id][own_key])
            allowed[team].append(game_values[game_id][opponent_key])
            if made_attempted:
                for index in (0, 1):
                    production_shots[team][index] += raw[game_id][own_key][index]
                    allowed_shots[team][index] += raw[game_id][opponent_key][index]
            if not _has_room(production[team], game_limit):
                break
    output: dict[str, tuple[int, float]] = {}
    for team, opponent in ((target_teams[0], target_teams[1]), (target_teams[1], target_teams[0])):
        if production[team] and allowed[opponent]:
            count = min(len(production[team]), len(allowed[opponent]))
            expected = ((sum(production[team]) / len(production[team])) +
                        (sum(allowed[opponent]) / len(allowed[opponent]))) / 2
            if made_attempted:
                own = production_shots[team]
                conceded = allowed_shots[opponent]
                expected = (own[0] / own[1] + conceded[0] / conceded[1]) * 50
            output[team] = (count, expected)
    return output


def _matching_option(team_name: str | None, options: list[str]) -> str | None:
    return next((option for option in options if team_name is not None and _same_team(option, team_name)), None)


def _same_team(first: str, second: str) -> bool:
    first_normalized, second_normalized = "".join(first.split()).casefold(), "".join(second.split()).casefold()
    return first_normalized in second_normalized or second_normalized in first_normalized
