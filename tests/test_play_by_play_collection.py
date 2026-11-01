from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.collectors.official_pages import (
    VisiblePlayByPlayEvent,
    _visible_play_by_play_periods,
)
from app.services.play_by_play_collection import (
    SpecialScoring,
    _derive_scoring_lead,
    _verify_bench_points,
    derive_special_scoring,
)


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
            event("8:20", 1, "나 굿디펜스"),
            event("8:10", 2, "아치 굿윈 턴오버"),
            event("8:00", 1, "카 3점슛성공"),
            event("7:30", 2, "바 2점슛성공"),
        ]
    )
    first, second = derive_special_scoring(events)
    assert (first.bench_points, first.second_chance_points) == (5, 2)
    assert (second.bench_points, second.second_chance_points) == (2, 2)
    assert (first.good_defense, second.good_defense) == (1, 0)


def test_rejects_text_broadcast_without_exact_starting_fives() -> None:
    events = tuple(event("10:00", 1, f"선수{i} 교체(IN)") for i in range(5))
    try:
        derive_special_scoring(events)
    except ValueError as error:
        assert "선발 5명" in str(error)
    else:
        raise AssertionError("missing starters must not be accepted")


def test_verifies_bench_points_against_complete_visible_box_score() -> None:
    session = MagicMock()
    session.scalars.return_value = [
        SimpleNamespace(player_name="선발 A", points=20),
        SimpleNamespace(player_name="벤치 B", points=7),
    ]
    result = SpecialScoring(1, 7, 0, 0, 0, 27, ("선발A", "선발2", "선발3", "선발4", "선발5"))
    _verify_bench_points(session, 1, "테스트 팀", 27, result)


def test_rejects_bench_points_that_contradict_complete_visible_box_score() -> None:
    session = MagicMock()
    session.scalars.return_value = [
        SimpleNamespace(player_name="선발 A", points=20),
        SimpleNamespace(player_name="벤치 B", points=7),
    ]
    result = SpecialScoring(1, 9, 0, 0, 0, 27, ("선발 A", "선발2", "선발3", "선발4", "선발5"))
    with pytest.raises(ValueError, match="공식 선수기록 합계"):
        _verify_bench_points(session, 1, "테스트 팀", 27, result)


def test_skips_cross_check_when_visible_box_score_is_incomplete() -> None:
    session = MagicMock()
    session.scalars.return_value = [SimpleNamespace(player_name="선발 A", points=20)]
    result = SpecialScoring(1, 9, 0, 0, 0, 20, ("선발 A", "선발2", "선발3", "선발4", "선발5"))
    _verify_bench_points(session, 1, "테스트 팀", 27, result)


def test_counts_overtime_scoring_and_resets_second_chance_at_period_boundary() -> None:
    regulation = [
        event("10:00", side, f"{name} 교체(IN)")
        for side, names in (
            (1, ("가", "나", "다", "라", "마")),
            (2, ("바", "사", "아", "자", "차")),
        )
        for name in names
    ]
    overtime = [
        VisiblePlayByPlayEvent(4, "0:01", 1, "카 공격리바운드"),
        VisiblePlayByPlayEvent(5, "4:50", 1, "카 2점슛성공"),
        VisiblePlayByPlayEvent(5, "4:20", 2, "타 공격리바운드"),
        VisiblePlayByPlayEvent(5, "4:10", 2, "타 3점슛성공"),
    ]
    first, second = derive_special_scoring(tuple(regulation + overtime))
    assert (first.bench_points, first.second_chance_points) == (2, 0)
    assert (second.bench_points, second.second_chance_points) == (3, 3)


def test_replays_same_clock_rows_in_reverse_screen_order() -> None:
    starters = [
        event("10:00", side, f"{name} 교체(IN)")
        for side, names in (
            (1, ("가", "나", "다", "라", "마")),
            (2, ("바", "사", "아", "자", "차")),
        )
        for name in names
    ]
    # The official table is newest-first: free throws are displayed above the
    # foul and offensive rebound that happened at the same clock value.
    newest_first = [
        event("5:00", 1, "카 자유투성공"),
        event("5:00", 1, "카 자유투성공"),
        event("5:00", 2, "바 파울자유투"),
        event("5:00", 1, "카 공격리바운드"),
    ]
    first, _second = derive_special_scoring(tuple(starters + newest_first))
    assert (first.bench_points, first.second_chance_points) == (2, 2)


def test_reads_visible_regulation_and_overtime_period_tabs() -> None:
    page = MagicMock()
    page.locator.return_value.all_inner_texts.return_value = ["Q1", "Q2", "Q3", "Q4", "EQ1", "EQ2"]
    assert _visible_play_by_play_periods(page) == [
        ("Q1", 1), ("Q2", 2), ("Q3", 3), ("Q4", 4), ("EQ1", 5), ("EQ2", 6),
    ]


def test_derives_scoring_lead_time_from_visible_score_changes() -> None:
    events = (
        event("9:00", 1, "가 2점슛성공"),
        event("7:00", 2, "바 3점슛성공"),
    )
    lead_seconds, scores = _derive_scoring_lead(events)
    assert scores == {1: 2, 2: 3}
    assert lead_seconds == {1: 120, 2: 2220}
