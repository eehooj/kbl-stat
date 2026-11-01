from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models import PlayerAvailability, StatsKingVisibleGame, VisiblePlayerSeasonStat
from app.services.stats_king_recommendation import (
    _is_unavailable,
    _latest_roster_snapshot,
    _leader,
    _recent_forms,
    _same_team,
)


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


def test_recent_form_does_not_override_a_higher_full_season_average() -> None:
    season_leader = VisiblePlayerSeasonStat(
        player_name="시즌 선두", team_name="고양 소노", games_played=10,
        points=200, rebounds=10, assists=10, source_url="https://example.test", observed_at=None,
    )
    recent_leader = VisiblePlayerSeasonStat(
        player_name="최근 선두", team_name="수원 KT", games_played=10,
        points=190, rebounds=10, assists=10, source_url="https://example.test", observed_at=None,
    )
    recent_forms = {
        ("시즌 선두", "고양 소노"): (5, {"points": 10.0}),
        ("최근 선두", "수원 KT"): (5, {"points": 40.0}),
    }
    leader = _leader("득점", "points", [season_leader, recent_leader], recent_forms)
    assert leader.player_name == "시즌 선두"


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


def test_uses_only_players_seen_in_the_latest_complete_roster_snapshot() -> None:
    old_snapshot = datetime(2026, 10, 30, tzinfo=UTC)
    current_snapshot = datetime(2026, 11, 1, tzinfo=UTC)
    stale = VisiblePlayerSeasonStat(
        player_name="이적 선수", team_name="이전 팀", games_played=3,
        points=30, rebounds=10, assists=5, source_url="https://example.test",
        observed_at=old_snapshot, roster_snapshot_at=old_snapshot,
    )
    current = VisiblePlayerSeasonStat(
        player_name="이적 선수", team_name="현재 팀", games_played=5,
        points=60, rebounds=20, assists=10, source_url="https://example.test",
        observed_at=current_snapshot, roster_snapshot_at=current_snapshot,
    )
    same_name_current = VisiblePlayerSeasonStat(
        player_name="이적 선수", team_name="동명이인 팀", games_played=2,
        points=12, rebounds=4, assists=3, source_url="https://example.test",
        observed_at=current_snapshot, roster_snapshot_at=current_snapshot,
    )
    assert _latest_roster_snapshot([stale, current, same_name_current]) == [
        current, same_name_current,
    ]


def test_requires_a_complete_roster_snapshot_before_recommending_players() -> None:
    legacy = VisiblePlayerSeasonStat(
        player_name="과거 선수", team_name="이전 팀", games_played=3,
        points=30, rebounds=10, assists=5, source_url="https://example.test",
        observed_at=datetime(2026, 10, 30, tzinfo=UTC), roster_snapshot_at=None,
    )
    assert _latest_roster_snapshot([legacy]) == []


def test_keeps_recent_form_separate_for_same_name_players_on_different_teams() -> None:
    snapshot = datetime(2026, 11, 1, tzinfo=UTC)
    candidates = [
        VisiblePlayerSeasonStat(
            player_name="이정현", team_name=team, games_played=5,
            points=50, rebounds=10, assists=10, source_url="https://example.test",
            observed_at=snapshot, roster_snapshot_at=snapshot,
        )
        for team in ("고양 소노", "원주 DB")
    ]
    observed = [
        (SimpleNamespace(player_name="이정현", team_name=team, points=points, rebounds=1, assists=1), snapshot)
        for team, points in (("고양 소노", 20), ("원주 DB", 4))
        for _ in range(3)
    ]
    session = MagicMock()
    session.execute.return_value.all.return_value = observed
    game = StatsKingVisibleGame(
        starts_at=datetime(2026, 11, 2, tzinfo=UTC), venue="테스트",
        first_team_name="고양소노", second_team_name="원주DB",
        participation_status="미참여", source_url="https://example.test", observed_at=snapshot,
        observed_key="test",
    )
    forms = _recent_forms(session, game, candidates)
    assert forms[("이정현", "고양 소노")][1]["points"] == 20
    assert forms[("이정현", "원주 DB")][1]["points"] == 4
