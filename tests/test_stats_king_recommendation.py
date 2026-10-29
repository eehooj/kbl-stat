from app.models import VisiblePlayerSeasonStat
from app.services.stats_king_recommendation import _leader, _same_team


def test_selects_the_highest_per_game_candidate_for_each_metric() -> None:
    high_average = VisiblePlayerSeasonStat(
        player_name="선수 A", team_name="울산 현대모비스", games_played=5,
        points=100, rebounds=40, assists=20, source_url="https://example.test", observed_at=None,
    )
    high_total = VisiblePlayerSeasonStat(
        player_name="선수 B", team_name="부산 KCC", games_played=10,
        points=180, rebounds=90, assists=80, source_url="https://example.test", observed_at=None,
    )
    leader = _leader("득점", "points", [high_average, high_total])
    assert (leader.player_name, leader.per_game) == ("선수 A", 20.0)


def test_normalizes_spacing_in_visible_team_names() -> None:
    assert _same_team("울산 현대모비스", "울산현대모비스")
