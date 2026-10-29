from datetime import datetime
from zoneinfo import ZoneInfo

from app.models import VisibleScheduleGame
from app.services.daily_picks_schedule_linking import (
    _option_teams_match,
    classify_visible_daily_pick,
)

KST = ZoneInfo("Asia/Seoul")


def test_classifies_only_metric_and_quarter_visible_in_question_text() -> None:
    assert classify_visible_daily_pick("4쿼터 더 많은 득점 기록하기?") == {
        "metric": "points", "quarter": 4, "classification_status": "classified",
    }
    assert classify_visible_daily_pick("어느 팀이 승리할까요?") == {
        "metric": None, "quarter": None, "classification_status": "unclassified",
    }


def test_matches_two_team_options_without_using_a_draw_option() -> None:
    game = VisibleScheduleGame(
        observed_key="game", season_id=1, starts_at=datetime(2026, 10, 29, 19, tzinfo=KST), competition="정규시즌",
        venue="울산동천체육관", first_team_name="현대모비스", second_team_name="KCC", first_score=None,
        second_score=None, status="scheduled", source_url="https://example.test", observed_at=datetime(2026, 10, 29, tzinfo=KST),
    )
    assert _option_teams_match(["울산현대모비스", "무승부", "부산KCC"], game)
