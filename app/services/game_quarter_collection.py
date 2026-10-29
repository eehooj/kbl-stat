"""Collect only visibly rendered quarter scores from public completed-game summaries."""
import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import RenderedPage
from app.models import VisibleGameQuarterScore, VisibleScheduleGame
from app.services.visible_record_collection import collect_rendered_page

TEAM_NAMES = (
    "원주 DB", "울산 현대모비스", "부산 KCC", "안양 정관장", "수원 KT",
    "창원 LG", "대구 한국가스공사", "고양 소노", "서울 삼성", "서울 SK",
)
RECORD_DATE = re.compile(r"/match/record/[^/]+/(?P<date>20\d{6})$")


@dataclass(frozen=True)
class VisibleQuarterScore:
    record_url: str
    game_date: datetime
    first_team_name: str
    second_team_name: str
    first_quarters: tuple[int, int, int, int]
    second_quarters: tuple[int, int, int, int]
    first_total: int
    second_total: int


def parse_visible_quarter_score(page: RenderedPage) -> VisibleQuarterScore:
    match = RECORD_DATE.search(page.url)
    if match is None:
        raise ValueError("경기 상세 URL에서 날짜를 확인할 수 없습니다")
    lines = [line.strip() for line in page.visible_text.splitlines() if line.strip()]
    table_index = lines.index("경기 기록 테이블") if "경기 기록 테이블" in lines else -1
    if table_index < 0:
        raise ValueError("경기요약 화면에 쿼터 점수 표가 표시되지 않았습니다")
    teams = [line for line in lines[:table_index] if line in TEAM_NAMES]
    if len(teams) < 2:
        raise ValueError("경기요약 화면에 두 팀 이름이 표시되지 않았습니다")
    score_rows = [
        [int(value) for value in line.split()]
        for line in lines[table_index + 1:table_index + 5]
        if re.fullmatch(r"\d+(?:\s+\d+){5}", line)
    ]
    if len(score_rows) != 2:
        raise ValueError("경기요약 화면의 쿼터 점수 행을 확인할 수 없습니다")
    year, month, day = int(match["date"][:4]), int(match["date"][4:6]), int(match["date"][6:])
    return VisibleQuarterScore(
        record_url=page.url, game_date=datetime(year, month, day), first_team_name=teams[0], second_team_name=teams[1],
        first_quarters=tuple(score_rows[0][:4]), second_quarters=tuple(score_rows[1][:4]),
        first_total=score_rows[0][-1], second_total=score_rows[1][-1],
    )


def collect_visible_quarter_scores(session: Session, pages: list[RenderedPage]) -> tuple[int, int]:
    saved = unlinked = 0
    for page in pages:
        score = parse_visible_quarter_score(page)
        game = _matching_schedule_game(session, score)
        collect_rendered_page(session, page, "visible game quarter score", commit=False)
        if game is None:
            unlinked += 1
            continue
        stored = session.scalar(select(VisibleGameQuarterScore).where(
            VisibleGameQuarterScore.schedule_game_id == game.id,
        ))
        fields = {
            "record_url": score.record_url,
            "first_team_name": score.first_team_name,
            "second_team_name": score.second_team_name,
            "first_quarters": list(score.first_quarters),
            "second_quarters": list(score.second_quarters),
            "first_total": score.first_total,
            "second_total": score.second_total,
            "source_url": page.url,
            "observed_at": page.fetched_at,
        }
        if stored is None:
            session.add(VisibleGameQuarterScore(schedule_game_id=game.id, **fields))
        else:
            for name, value in fields.items():
                setattr(stored, name, value)
        saved += 1
    session.commit()
    return saved, unlinked


def _matching_schedule_game(session: Session, score: VisibleQuarterScore) -> VisibleScheduleGame | None:
    candidates = [
        game for game in session.scalars(select(VisibleScheduleGame).where(VisibleScheduleGame.status == "final"))
        if game.starts_at.date() == score.game_date.date()
        and _same_team_pair(
            (game.first_team_name, game.second_team_name), (score.first_team_name, score.second_team_name),
        )
    ]
    return candidates[0] if len(candidates) == 1 else None


def _normalized(value: str) -> str:
    return "".join(value.split()).casefold()


def _same_team_pair(first: tuple[str, str], second: tuple[str, str]) -> bool:
    return all(any(_labels_equivalent(left, right) for right in second) for left in first)


def _labels_equivalent(first: str, second: str) -> bool:
    first_normalized, second_normalized = _normalized(first), _normalized(second)
    return first_normalized in second_normalized or second_normalized in first_normalized
