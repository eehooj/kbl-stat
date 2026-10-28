from datetime import UTC, datetime

from app.collectors.official_pages import RenderedPage
from app.services.weekly6_collection import (
    Weekly6Visibility,
    inspect_weekly6_page,
    parse_visible_weekly6,
)


def page(text: str) -> RenderedPage:
    return RenderedPage(
        url="https://www.kbl.or.kr/game/challenge/weekly6", fetched_at=datetime.now(UTC), title="KBL", visible_text=text,
        content_hash="a" * 64,
    )


def test_marks_a_footer_only_page_as_body_not_visible() -> None:
    assert inspect_weekly6_page(page("KBL 소개\n이용약관\nCopyright")) is Weekly6Visibility.BODY_NOT_VISIBLE


def test_marks_a_visible_weekly6_page_without_extracting_fields() -> None:
    assert inspect_weekly6_page(page("Weekly 6\n응모를 위한 6 경기 중 0 경기 선택")) is Weekly6Visibility.BODY_VISIBLE


def test_parses_visible_weekly6_candidates_without_home_away_inference() -> None:
    round_ = parse_visible_weekly6(page("""Weekly 6
Pick 1
2026.10.26 19:00
고양소노아레나
고양소노
창원LG
Pick 2
2026.11.01 16:30
잠실학생체육관
서울삼성
서울SK
응모를 위한 6경기 중 0경기 선택
"""))
    assert round_.week_label == "2026-10-26~2026-11-01"
    assert round_.selection_count == 6
    assert round_.fixtures[0].first_team_name == "고양소노"
