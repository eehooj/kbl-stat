from datetime import datetime
from zoneinfo import ZoneInfo

from app.models import VisibleScheduleGame
from app.services.team_form_features import calculate_team_forms, parse_as_of

KST = ZoneInfo("Asia/Seoul")


def _game(day: int, first: str, second: str, first_score: int, second_score: int) -> VisibleScheduleGame:
    return VisibleScheduleGame(
        observed_key=f"game-{day}", season_id=1, starts_at=datetime(2026, 10, day, 19, tzinfo=KST),
        competition="정규시즌", venue="경기장", first_team_name=first, second_team_name=second,
        first_score=first_score, second_score=second_score, status="final", source_url="https://example.test",
        observed_at=datetime(2026, 10, day, 22, tzinfo=KST),
    )


def test_calculate_team_forms_excludes_results_at_or_after_cutoff() -> None:
    games = [
        _game(1, "A", "B", 80, 70),
        _game(3, "A", "C", 70, 80),
        _game(5, "A", "D", 90, 80),
        _game(8, "A", "E", 100, 90),
    ]
    forms = calculate_team_forms(games, datetime(2026, 10, 8, 19, tzinfo=KST))
    form = next(item for item in forms if item.team_name == "A")
    assert (form.games_played, form.wins, form.losses) == (3, 2, 1)
    assert (form.recent_five_wins, form.recent_ten_wins) == (2, 2)
    assert form.average_points_for == 80
    assert form.average_points_against == 76 + 2 / 3
    assert form.rest_days == 2


def test_parse_as_of_defaults_to_kst_for_a_naive_value() -> None:
    assert parse_as_of("2026-10-29T19:00").isoformat() == "2026-10-29T19:00:00+09:00"
