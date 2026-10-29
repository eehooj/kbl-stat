from datetime import UTC, datetime

from app.collectors.official_pages import RenderedPage
from app.services.daily_picks_collection import parse_visible_daily_picks


def test_parses_visible_daily_picks_questions_and_options() -> None:
    page = RenderedPage(
        url="https://www.kbl.or.kr/game/challenge/daily-picks", fetched_at=datetime.now(UTC), title="Daily Picks",
        content_hash="a" * 64, visible_text="""Daily Picks
2026.10.29
Pick 1
19:00
울산동천체육관
현대모비스
4쿼터 더 많은 득점 기록하기?
울산현대모비스
무승부
부산KCC
Pick 2
19:00
울산동천체육관
현대모비스
2쿼터 더 많은 득점 기록하기?
울산현대모비스
무승부
부산KCC
""",
    )
    picks = parse_visible_daily_picks(page)
    assert len(picks) == 2
    assert picks[0].starts_at.isoformat() == "2026-10-29T19:00:00+09:00"
    assert picks[0].options == ("울산현대모비스", "무승부", "부산KCC")
