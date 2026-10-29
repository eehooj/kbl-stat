from datetime import datetime
from zoneinfo import ZoneInfo

from app.models import VisibleScheduleGame, Weekly6VisibleFixture
from app.services.weekly6_schedule_linking import find_visible_schedule_match

KST = ZoneInfo("Asia/Seoul")


def test_links_candidates_by_visible_time_venue_and_team_label_containment() -> None:
    starts_at = datetime(2026, 10, 26, 19, tzinfo=KST)
    fixture = Weekly6VisibleFixture(
        round_id=1, ordinal=1, starts_at=starts_at, venue="고양소노아레나",
        first_team_name="고양소노", second_team_name="창원LG", source_url="https://example.test", observed_at=starts_at,
    )
    game = VisibleScheduleGame(
        observed_key="schedule-1", season_id=1, starts_at=starts_at, competition="정규시즌", venue="고양소노아레나",
        first_team_name="소노", second_team_name="LG", first_score=None, second_score=None, status="scheduled",
        source_url="https://example.test", observed_at=starts_at,
    )
    assert find_visible_schedule_match(fixture, [game]) is game


def test_does_not_link_when_the_visible_venue_differs() -> None:
    starts_at = datetime(2026, 10, 26, 19, tzinfo=KST)
    fixture = Weekly6VisibleFixture(
        round_id=1, ordinal=1, starts_at=starts_at, venue="고양소노아레나",
        first_team_name="고양소노", second_team_name="창원LG", source_url="https://example.test", observed_at=starts_at,
    )
    game = VisibleScheduleGame(
        observed_key="schedule-1", season_id=1, starts_at=starts_at, competition="정규시즌", venue="다른경기장",
        first_team_name="소노", second_team_name="LG", first_score=None, second_score=None, status="scheduled",
        source_url="https://example.test", observed_at=starts_at,
    )
    assert find_visible_schedule_match(fixture, [game]) is None
