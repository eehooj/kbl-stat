from datetime import UTC, datetime

from app.collectors.official_pages import RenderedPage
from app.services.player_game_stat_collection import parse_visible_player_box_scores


def test_parses_visible_home_and_away_player_box_score_rows() -> None:
    page = RenderedPage(
        url="https://www.kbl.or.kr/match/record/S49G01N1/20261003", fetched_at=datetime.now(UTC), title="KBL",
        content_hash="a" * 64, visible_text="""홈 선수기록
No. 선수명 Min PTS 2PM 2PA 2P% 3PM 3PA 3P% FGM FGA FG% FTM FTA FT% OREB DREB REB AST STL BLK GD DK DKA SAST DFL TO PF PP PPA PP% +/-
7
선수 A
28:38 4 2 6 33.3 0 4 0.0 2 10 20.0 0 2 0.0 0 0 0 7 0 0 0 0 0 0 1 3 1 1 4 25.0 -34
6
미출전 선수
미출전
계
원정 선수기록
No. 선수명 Min PTS 2PM 2PA 2P% 3PM 3PA 3P% FGM FGA FG% FTM FTA FT% OREB DREB REB AST STL BLK GD DK DKA SAST DFL TO PF PP PPA PP% +/-
8
선수 B
25:52 25 5 8 62.5 3 10 30.0 8 18 44.4 6 10 60.0 1 1 2 2 1 0 1 0 0 1 0 2 1 4 7 57.1 21
계
""",
    )
    rows = parse_visible_player_box_scores(page, "부산 KCC", "창원 LG")
    assert [(row.player_name, row.team_name, row.points, row.assists) for row in rows] == [
        ("선수 A", "부산 KCC", 4, 7), ("선수 B", "창원 LG", 25, 2),
    ]
