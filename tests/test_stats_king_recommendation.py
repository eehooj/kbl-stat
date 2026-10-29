from datetime import date

from app.models import PlayerAvailability, VisiblePlayerSeasonStat
from app.services.stats_king_recommendation import _is_unavailable, _leader, _same_team


def test_selects_the_highest_per_game_candidate_for_each_metric() -> None:
    high_average = VisiblePlayerSeasonStat(
        player_name="선수 A", team_name="울산 현대모비스", games_played=5,
        points=100, rebounds=40, assists=20, source_url="https://example.test", observed_at=None,
    )
    high_total = VisiblePlayerSeasonStat(
        player_name="선수 B", team_name="부산 KCC", games_played=10,
        points=180, rebounds=90, assists=80, source_url="https://example.test", observed_at=None,
    )
    leader = _leader("득점", "points", [high_average, high_total], {})
    assert (leader.player_name, leader.per_game) == ("선수 A", 20.0)


def test_normalizes_spacing_in_visible_team_names() -> None:
    assert _same_team("울산 현대모비스", "울산현대모비스")


def test_excludes_a_player_only_for_a_matching_date_and_team() -> None:
    player = VisiblePlayerSeasonStat(
        player_name="게이지 프림", team_name="울산 현대모비스", games_played=8,
        points=164, rebounds=51, assists=20, source_url="https://example.test", observed_at=None,
    )
    unavailable = PlayerAvailability(
        player_name="게이지 프림", team_name="울산 현대모비스", availability_date=date(2026, 10, 29),
        status="out", source_note="사용자 확인", verified_at=None,
    )
    assert _is_unavailable(player, [unavailable])
