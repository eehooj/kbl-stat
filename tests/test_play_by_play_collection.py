from app.collectors.official_pages import VisiblePlayByPlayEvent
from app.services.play_by_play_collection import derive_special_scoring


def event(clock: str, side: int, description: str) -> VisiblePlayByPlayEvent:
    return VisiblePlayByPlayEvent(1, clock, side, description)


def test_derives_bench_and_second_chance_points_from_visible_events() -> None:
    events = tuple(
        [event("10:00", side, f"{name} 교체(IN)") for side, names in (
            (1, ("가", "나", "다", "라", "마")),
            (2, ("바", "사", "아", "자", "차")),
        ) for name in names]
        + [
            event("9:30", 1, "가 2점슛시도"),
            event("9:29", 1, "카 공격리바운드"),
            event("9:20", 1, "카 2점슛성공"),
            event("8:50", 2, "타 공격리바운드"),
            event("8:45", 2, "타 자유투성공"),
            event("8:45", 2, "타 자유투성공"),
            event("8:30", 1, "가 수비리바운드"),
            event("8:00", 1, "카 3점슛성공"),
            event("7:30", 2, "바 2점슛성공"),
        ]
    )
    first, second = derive_special_scoring(events)
    assert (first.bench_points, first.second_chance_points) == (5, 2)
    assert (second.bench_points, second.second_chance_points) == (2, 2)


def test_rejects_text_broadcast_without_exact_starting_fives() -> None:
    events = tuple(event("10:00", 1, f"선수{i} 교체(IN)") for i in range(5))
    try:
        derive_special_scoring(events)
    except ValueError as error:
        assert "선발 5명" in str(error)
    else:
        raise AssertionError("missing starters must not be accepted")
