from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.daily_picks_recommendation import _opponent_adjusted_averages


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
