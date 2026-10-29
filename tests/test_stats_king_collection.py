from datetime import UTC, datetime

from app.collectors.official_pages import RenderedPage
from app.services.stats_king_collection import LOGIN_REQUIRED_TEXT, parse_visible_stats_king_game


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


def test_login_gate_text_is_explicit() -> None:
    assert LOGIN_REQUIRED_TEXT == "로그인 후 이용해주세요."
