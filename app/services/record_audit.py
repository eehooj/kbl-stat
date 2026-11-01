"""Read-only checks against independently stored official final scores."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import VisibleGameQuarterScore, VisiblePlayerGameStat


def verified_game_ids(session: Session) -> set[int]:
    grouped: dict[int, list[bool]] = {}
    for game, _team, actual, expected in audit_box_scores(session):
        grouped.setdefault(game, []).append(actual >= 0 and expected >= 0 and actual == expected)
    return {game for game, checks in grouped.items() if len(checks) == 2 and all(checks)}


def audit_box_scores(session: Session) -> list[tuple[int, str, int, int]]:
    totals: dict[tuple[int, str], int] = {}
    for row in session.scalars(select(VisiblePlayerGameStat)):
        key = (row.schedule_game_id, row.team_name)
        totals[key] = totals.get(key, 0) + row.points
    results = []
    checked = set()
    for score in session.scalars(select(VisibleGameQuarterScore)):
        for team, expected in ((score.first_team_name, score.first_total), (score.second_team_name, score.second_total)):
            actual = totals.get((score.schedule_game_id, team), -1)
            results.append((score.schedule_game_id, team, actual, expected))
            checked.add((score.schedule_game_id, team))
    for (game_id, team), actual in totals.items():
        if (game_id, team) not in checked:
            results.append((game_id, team, actual, -1))
    return results
