from datetime import UTC, datetime

from app.collectors.official_pages import RenderedPage
from app.services.stats_king_collection import (
    parse_visible_stats_king_game,
    parse_visible_stats_king_games,
)


def test_parses_only_a_complete_visible_stats_king_game_card() -> None:
    page = RenderedPage(
        url="https://www.kbl.or.kr/game/challenge/stats", fetched_at=datetime.now(UTC), title="StatsKing",
        content_hash="a" * 64, visible_text="""StatsKing
2026.10.29
내 선택 보기
미참여
19:00
울산동천
게임 마감까지 00일 05:47:05남았습니다.
울산현대모비스
부산KCC
게임참여
""",
    )
    game = parse_visible_stats_king_game(page)
    assert game is not None
    assert game.starts_at.isoformat() == "2026-10-29T19:00:00+09:00"
    assert game.first_team_name == "울산현대모비스"
    assert game.second_team_name == "부산KCC"


def test_does_not_make_a_game_from_an_incomplete_card() -> None:
    page = RenderedPage(
        url="https://www.kbl.or.kr/game/challenge/stats", fetched_at=datetime.now(UTC), title="StatsKing",
        content_hash="a" * 64, visible_text="StatsKing\n2026.10.29\n내 선택 보기\n",
    )
    assert parse_visible_stats_king_game(page) is None


def test_parses_every_visible_weekly_pick_card() -> None:
    page = RenderedPage(
        url="https://www.kbl.or.kr/game/challenge/stats-king", fetched_at=datetime.now(UTC), title="StatsKing",
        content_hash="b" * 64, visible_text="""StatsKing
게임이 마감되었습니다.
내 선택 보기
Pick 9
2026.11.01 14:00
고양소노아레나
고양소노
수원KT
Pick 10
2026.11.01 14:00
창원체육관
창원LG
원주DB
Pick 11
2026.11.01 16:30
잠실학생체육관
서울삼성
서울SK
""",
    )
    games = parse_visible_stats_king_games(page)
    assert [(game.first_team_name, game.second_team_name) for game in games] == [
        ("고양소노", "수원KT"), ("창원LG", "원주DB"), ("서울삼성", "서울SK"),
    ]


def test_parses_every_visible_game_on_current_day() -> None:
    page = RenderedPage(
        url="https://www.kbl.or.kr/game/challenge/stats", fetched_at=datetime.now(UTC), title="StatsKing",
        content_hash="c" * 64, visible_text="""StatsKing
오늘
2026.11.01
내 선택 보기
미참여
14:00
고양소노아레나
게임 마감까지 00일 00:10:00남았습니다.
고양소노
수원KT
게임참여
미참여
14:00
창원체육관
게임 마감까지 00일 00:10:00남았습니다.
창원LG
원주DB
게임참여
미참여
16:30
잠실학생
게임 마감까지 00일 02:40:00남았습니다.
서울삼성
서울SK
게임참여
팀 순위
""",
    )
    games = parse_visible_stats_king_games(page)
    assert [(game.first_team_name, game.second_team_name) for game in games] == [
        ("고양소노", "수원KT"), ("창원LG", "원주DB"), ("서울삼성", "서울SK"),
    ]
