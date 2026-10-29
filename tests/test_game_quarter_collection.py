from datetime import UTC, datetime

from app.collectors.official_pages import RenderedPage
from app.services.game_quarter_collection import _same_team_pair, parse_visible_quarter_score


def test_parses_visible_team_quarter_scores() -> None:
    page = RenderedPage(
        url="https://www.kbl.or.kr/match/record/S49G01N1/20261003", fetched_at=datetime.now(UTC), title="KBL",
        content_hash="a" * 64, visible_text="""부산 KCC
68
창원 LG
103
경기 기록 테이블
1Q 2Q 3Q 4Q EQ TOTAL
20 10 22 16 0 68
25 28 22 28 0 103
""",
    )
    score = parse_visible_quarter_score(page)
    assert score.first_team_name == "부산 KCC"
    assert score.first_quarters == (20, 10, 22, 16)
    assert score.second_total == 103


def test_matches_short_schedule_team_labels_to_detail_team_labels() -> None:
    assert _same_team_pair(("KCC", "LG"), ("부산 KCC", "창원 LG"))
