from app.services.visible_schedule_collection import parse_visible_schedule


def test_parse_visible_schedule_distinguishes_finished_and_scheduled_games() -> None:
    text = """일정 및 결과
2026 . 10
10.03
정규시즌
14:00
부산사직체육관
KCC 68
LG 103
기록
프리뷰
하이라이트
10.28
정규시즌
19:00
대구체육관
한국가스공사 0
DB 0
티켓예매
프리뷰
Challenge
"""
    fixtures = parse_visible_schedule(text)
    assert len(fixtures) == 2
    assert fixtures[0].status == "final"
    assert fixtures[0].first_score == 68
    assert fixtures[0].second_team_name == "LG"
    assert fixtures[1].status == "scheduled"
    assert fixtures[1].first_score is None
    assert fixtures[1].second_score is None
    assert fixtures[1].starts_at.isoformat() == "2026-10-28T19:00:00+09:00"


def test_parse_visible_schedule_supports_one_cell_per_line() -> None:
    text = """2026. 10
10.03
정규시즌
14:00
부산사직체육관
KCC
68
LG
103
기록
프리뷰
하이라이트
"""
    fixture = parse_visible_schedule(text)[0]
    assert (fixture.first_team_name, fixture.first_score) == ("KCC", 68)
    assert (fixture.second_team_name, fixture.second_score) == ("LG", 103)
