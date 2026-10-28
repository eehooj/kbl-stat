from app.services.visible_team_ranking_collection import parse_visible_team_rankings


def test_parse_visible_team_rankings() -> None:
    text = """팀 순위
2026-2027
정규경기 순위 테이블
순위
팀
승
패
승률
승차
최근 5경기
연속
홈
원정
다음경기
상대전적
1
서울 삼성
8
0
1.000
0
승승승승승
8승
4 - 0
4 - 0
고양 소노
1승0패
2
서울 SK
4
1
0.800
2.5
패승승승승
4승
4 - 1
0 - 0
서울 삼성
0승0패
"""
    season, rows = parse_visible_team_rankings(text)
    assert season == "2026-2027"
    assert [(row.team_name, row.wins, row.home_record) for row in rows] == [
        ("서울 삼성", 8, "4 - 0"),
        ("서울 SK", 4, "4 - 1"),
    ]
