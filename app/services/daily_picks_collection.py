"""Collect Daily Picks questions and options visibly rendered by the official page."""
import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import RenderedPage
from app.models import ChallengeOption, ChallengeQuestion, ChallengeType
from app.services.daily_picks_schedule_linking import link_daily_picks_schedule_games
from app.services.visible_record_collection import collect_rendered_page

KST = ZoneInfo("Asia/Seoul")
PICK = re.compile(r"^Pick\s+(?P<ordinal>\d+)$")
DATE = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")
TIME = re.compile(r"^\d{2}:\d{2}$")


@dataclass(frozen=True)
class VisibleDailyPick:
    ordinal: int
    starts_at: datetime
    venue: str
    subject_label: str
    question_text: str
    options: tuple[str, str, str]


def parse_visible_daily_picks(page: RenderedPage) -> list[VisibleDailyPick]:
    lines = [line.strip() for line in page.visible_text.splitlines() if line.strip()]
    date = next((line for line in lines if DATE.fullmatch(line)), None)
    if date is None:
        raise ValueError("Daily Picks 화면에 문제 날짜가 표시되지 않았습니다")
    picks: list[VisibleDailyPick] = []
    index = 0
    while index < len(lines):
        pick = PICK.match(lines[index])
        if pick is None:
            index += 1
            continue
        if index + 7 >= len(lines) or TIME.fullmatch(lines[index + 1]) is None:
            raise ValueError("Daily Picks 문제의 화면 표시 형식을 확인할 수 없습니다")
        starts_at = datetime.strptime(f"{date} {lines[index + 1]}", "%Y.%m.%d %H:%M").replace(tzinfo=KST)
        picks.append(VisibleDailyPick(
            ordinal=int(pick["ordinal"]), starts_at=starts_at, venue=lines[index + 2],
            subject_label=lines[index + 3], question_text=lines[index + 4],
            options=(lines[index + 5], lines[index + 6], lines[index + 7]),
        ))
        index += 8
    if not picks:
        raise ValueError("Daily Picks 문제가 화면에 표시되지 않았습니다")
    return picks


def collect_visible_daily_picks(session: Session, page: RenderedPage) -> tuple[int, int]:
    picks = parse_visible_daily_picks(page)
    collect_rendered_page(session, page, f"visible Daily Picks questions={len(picks)}", commit=False)
    for pick in picks:
        question = session.scalar(select(ChallengeQuestion).where(
            ChallengeQuestion.challenge_type == ChallengeType.DAILY_PICKS,
            ChallengeQuestion.question_date == pick.starts_at,
            ChallengeQuestion.text == pick.question_text,
        ))
        payload = {"ordinal": pick.ordinal, "venue": pick.venue, "subject_label": pick.subject_label}
        if question is None:
            question = ChallengeQuestion(
                challenge_type=ChallengeType.DAILY_PICKS, official_id=None, question_date=pick.starts_at,
                text=pick.question_text, closes_at=None, source_url=page.url, raw_payload=payload,
            )
            session.add(question)
            session.flush()
        else:
            question.source_url = page.url
            question.raw_payload = payload
        existing_options = {
            item.label: item
            for item in session.scalars(select(ChallengeOption).where(ChallengeOption.question_id == question.id))
        }
        for option_ordinal, label in enumerate(pick.options, start=1):
            if label not in existing_options:
                session.add(ChallengeOption(
                    question_id=question.id, official_id=None, label=label,
                    payload={"ordinal": option_ordinal},
                ))
    session.commit()
    linked = link_daily_picks_schedule_games(session)
    return len(picks), linked
