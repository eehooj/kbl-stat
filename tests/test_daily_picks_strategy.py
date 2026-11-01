from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.daily_picks_recommendation import (
    _opponent_adjusted_averages,
    _recent_shooting_percentages,
    _recent_team_averages,
)


def test_last_selected_game_includes_all_players_but_not_older_games() -> None:
    target = SimpleNamespace(starts_at=datetime(2026, 11, 1), first_team_name="A", second_team_name="B")
    rows = [
        (SimpleNamespace(team_name="A", points=points, made=made, attempted=attempts), SimpleNamespace(id=game))
        for game, points, made, attempts in [(1, 10, 1, 2), (1, 20, 1, 8), (2, 99, 99, 99)]
    ]
    session = MagicMock()
    session.execute.return_value.all.return_value = rows
    assert _recent_team_averages(session, target, "points", 1) == {"A": (1, 30.0)}
    assert _recent_shooting_percentages(session, target, "made", "attempted", 1) == {"A": (1, 20.0)}


def test_opponent_shooting_uses_total_attempts_not_average_of_percentages() -> None:
    target = SimpleNamespace(starts_at=datetime(2026, 11, 1), first_team_name="A", second_team_name="B")
    rows = []
    for game_id, made, attempts in [(1, 1, 1), (2, 0, 9)]:
        game = SimpleNamespace(id=game_id, first_team_name="A", second_team_name="B")
        for team in ("A", "B"):
            rows.append((SimpleNamespace(team_name=team, three_point_made=made, three_point_attempted=attempts), game))
    session = MagicMock()
    session.execute.return_value.all.return_value = rows
    assert _opponent_adjusted_averages(session, target, "three_point_pct", 5) == {
        "A": (2, 10.0), "B": (2, 10.0),
    }


def test_combines_team_production_with_opponents_recent_allowed_average() -> None:
    target = SimpleNamespace(
        starts_at=datetime(2026, 11, 1), first_team_name="A", second_team_name="B",
    )
    game_a = SimpleNamespace(
        id=1, first_team_name="A", second_team_name="C", starts_at=datetime(2026, 10, 30),
    )
    game_b = SimpleNamespace(
        id=2, first_team_name="B", second_team_name="D", starts_at=datetime(2026, 10, 30),
    )
    rows = [
        (SimpleNamespace(team_name="A", points=10), game_a),
        (SimpleNamespace(team_name="C", points=20), game_a),
        (SimpleNamespace(team_name="B", points=30), game_b),
        (SimpleNamespace(team_name="D", points=40), game_b),
    ]
    session = MagicMock()
    session.execute.return_value.all.return_value = rows
    result = _opponent_adjusted_averages(session, target, "points", 5)
    assert result == {"A": (1, 25.0), "B": (1, 25.0)}
