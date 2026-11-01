from datetime import UTC, datetime

import pytest

from app.collectors.official_pages import (
    RenderedDailyPicksResultPage,
    RenderedPage,
    _daily_picks_question_text,
)
from app.database import Base, make_session_factory
from app.models import ChallengeQuestion, ChallengeResult
from app.services.daily_picks_result_collection import collect_visible_daily_picks_results


def result_page(correct: tuple[str, ...]) -> RenderedDailyPicksResultPage:
    page = RenderedPage(
        url="https://www.kbl.or.kr/game/challenge/daily-picks",
        fetched_at=datetime.now(UTC), title="Daily Picks", content_hash="a" * 64,
        visible_text="""Daily Picks
2026.10.31
Pick 1
14:00
부산사직체육관
부산KCC
스틸이 더 많은 팀은 어디일까요?
부산KCC
동률
원주DB
""",
    )
    return RenderedDailyPicksResultPage(page, correct)


def test_stores_visible_official_answer_for_completed_daily_pick() -> None:
    factory = make_session_factory("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(factory.kw["bind"])
    with factory() as session:
        assert collect_visible_daily_picks_results(session, [result_page(("원주DB",))]) == (1, 1)
        question = session.query(ChallengeQuestion).one()
        result = session.query(ChallengeResult).one()
        assert result.question_id == question.id
        assert result.official_answer["label"] == "원주DB"


def test_rejects_answer_count_that_does_not_match_visible_questions() -> None:
    factory = make_session_factory("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(factory.kw["bind"])
    with factory() as session, pytest.raises(ValueError, match="문제 수와 화면상 정답 수"):
        collect_visible_daily_picks_results(session, [result_page(("원주DB", "부산KCC"))])


def test_excludes_masked_winner_list_from_retained_question_evidence() -> None:
    text = "Daily Picks\nPick 1\n질문\n정답자\n김*정 010-****-0000"
    assert _daily_picks_question_text(text) == "Daily Picks\nPick 1\n질문"
