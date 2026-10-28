from app.services.visible_record_collection import parse_season_leaders


def test_parse_visible_season_leader_rows() -> None:
    text = """기록
2026-2027
1차 스탯
득점
1 케렘 칸터 서울 삼성 26.1
2 패리스 배스 수원 KT 26.0
리바운드
1 아셈 마레이 창원 LG 14.3
"""
    season, leaders = parse_season_leaders(text)
    assert season == "2026-2027"
    assert [(item.metric, item.player_name, item.value) for item in leaders] == [
        ("득점", "케렘 칸터", 26.1),
        ("득점", "패리스 배스", 26.0),
        ("리바운드", "아셈 마레이", 14.3),
    ]


def test_parse_cell_per_line_rendered_rows() -> None:
    text = """2026-2027
득점
1
케렘 칸터
서울 삼성
26.1
"""
    _, leaders = parse_season_leaders(text)
    assert leaders[0].player_name == "케렘 칸터"
