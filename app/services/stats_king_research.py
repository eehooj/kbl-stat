"""Chronological box-score-only research; no present-day season totals in past tests."""
from collections import defaultdict
from datetime import date

from sqlalchemy import select

from app.models import VisiblePlayerGameStat, VisibleScheduleGame
from app.services.record_audit import verified_game_ids

METRICS = ("points", "rebounds", "assists")


def shrink_average(total: float, games: int, prior_mean: float, prior_games: float = 3) -> float:
    if games <= 0 or prior_games < 0:
        raise ValueError("positive games and nonnegative prior strength required")
    return (total + prior_games * prior_mean) / (games + prior_games)


def evaluate_shrinkage(session, since: date) -> str:
    verified = verified_game_ids(session)
    games = list(session.scalars(select(VisibleScheduleGame).order_by(VisibleScheduleGame.starts_at)))
    stats = defaultdict(list)
    for row in session.scalars(select(VisiblePlayerGameStat)):
        if row.schedule_game_id in verified:
            stats[row.schedule_game_id].append(row)
    history = defaultdict(list)
    score = {strategy: [0, 0] for strategy in ("원평균", "보정평균")}
    details = []
    # Games with identical start times are evaluated before any of that batch enters history.
    batches = defaultdict(list)
    for game in games:
        if game.id in stats:
            batches[game.starts_at].append(game)
    for starts_at, batch in batches.items():
        for game in batch:
            actual = stats[game.id]
            teams = {row.team_name for row in actual}
            candidates = {key: rows for key, rows in history.items() if key[0] in teams}
            if starts_at.date() < since or not candidates:
                continue
            for metric in METRICS:
                prior_rows = [row for rows in history.values() for row in rows]
                prior_mean = sum(getattr(row, metric) for row in prior_rows) / len(prior_rows)
                winners = {(row.team_name, row.player_name) for row in actual
                           if getattr(row, metric) == max(getattr(other, metric) for other in actual)}
                picks = []
                for strategy, strength in (("원평균", 0), ("보정평균", 3)):
                    selected = max(candidates, key=lambda key: (
                        shrink_average(sum(getattr(row, metric) for row in candidates[key]),
                                       len(candidates[key]), prior_mean, strength), key,
                    ))
                    score[strategy][0] += 1
                    score[strategy][1] += selected in winners
                    picks.append(f"{strategy}={selected[1]} ({'적중' if selected in winners else '실패'})")
                details.append(f"{starts_at.date()} {game.first_team_name}-{game.second_team_name} {metric}: "
                               + ", ".join(picks))
        for game in batch:
            for row in stats[game.id]:
                history[(row.team_name, row.player_name)].append(row)
    lines = [f"StatsKing 소표본 연구: {since} 이후, 사전 경기기록만 사용",
             "사전 등록·결장 이력 미복원: 과거 출전 선수 후보 기준의 연구이며 실제 추천 적중률이 아닙니다.",
             "보정: 리그 이전 선수-경기 평균 3경기분을 추가. 동률 1위 포함."]
    for strategy, (count, hits) in score.items():
        lines.append(f"{strategy}: {hits}/{count}" + (f" ({hits/count:.1%})" if count else " 평가 불가"))
    return "\n".join(lines + details)
