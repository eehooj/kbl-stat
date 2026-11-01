"""Collect official Daily Picks answers visibly marked on completed-day screens."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import RenderedDailyPicksResultPage
from app.models import ChallengeOption, ChallengeQuestion, ChallengeResult, ChallengeType
from app.services.daily_picks_collection import (
    collect_visible_daily_picks,
    parse_visible_daily_picks,
)


def collect_visible_daily_picks_results(
    session: Session, pages: list[RenderedDailyPicksResultPage],
) -> tuple[int, int]:
    questions_saved = answers_saved = 0
    for rendered in pages:
        picks = parse_visible_daily_picks(rendered.page)
        if not rendered.correct_option_labels:
            continue
        if len(rendered.correct_option_labels) != len(picks):
            raise ValueError("Daily Picks 문제 수와 화면상 정답 수가 다릅니다")
        count, _linked = collect_visible_daily_picks(session, rendered.page)
        questions_saved += count
        for pick, answer_label in zip(picks, rendered.correct_option_labels):
            if answer_label not in pick.options:
                raise ValueError("Daily Picks 화면상 정답이 문제 선택지에 없습니다")
            question = session.scalar(select(ChallengeQuestion).where(
                ChallengeQuestion.challenge_type == ChallengeType.DAILY_PICKS,
                ChallengeQuestion.question_date == pick.starts_at,
                ChallengeQuestion.text == pick.question_text,
            ))
            if question is None:
                raise ValueError("저장된 Daily Picks 문제를 정답과 연결할 수 없습니다")
            option = session.scalar(select(ChallengeOption).where(
                ChallengeOption.question_id == question.id,
                ChallengeOption.label == answer_label,
            ))
            if option is None:
                raise ValueError("저장된 Daily Picks 선택지를 정답과 연결할 수 없습니다")
            result = session.scalar(select(ChallengeResult).where(
                ChallengeResult.question_id == question.id,
            ))
            fields = {
                "official_answer": {"option_id": option.id, "label": answer_label},
                "scoring_rule": {"evidence": "visible disabled option marked true"},
                "verified_at": rendered.page.fetched_at,
            }
            if result is None:
                session.add(ChallengeResult(question_id=question.id, **fields))
            else:
                for name, value in fields.items():
                    setattr(result, name, value)
            answers_saved += 1
        session.commit()
    return questions_saved, answers_saved
