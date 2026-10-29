"""Collect Weekly 6 candidates only when they are visibly rendered."""
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.collectors.official_pages import RenderedPage
from app.models import Weekly6Round, Weekly6VisibleFixture
from app.services.visible_record_collection import collect_rendered_page
from app.services.weekly6_schedule_linking import link_weekly6_schedule_games

KST = ZoneInfo("Asia/Seoul")
PICK = re.compile(r"^Pick\s+(?P<ordinal>\d+)$")
STARTS_AT = re.compile(r"^\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}$")
SELECTION_COUNT = re.compile(r"응모를 위한\s*(?P<count>\d+)\s*경기")


class Weekly6Visibility(StrEnum):
    BODY_VISIBLE = "body_visible"
    BODY_NOT_VISIBLE = "body_not_visible"


@dataclass(frozen=True)
class VisibleWeekly6Fixture:
    ordinal: int
    starts_at: datetime
    venue: str
    first_team_name: str
    second_team_name: str


@dataclass(frozen=True)
class VisibleWeekly6Round:
    week_label: str
    selection_count: int | None
    fixtures: tuple[VisibleWeekly6Fixture, ...]


def inspect_weekly6_page(page: RenderedPage) -> Weekly6Visibility:
    """Do not equate a missing page body with a missing Weekly 6 round."""
    normalized = " ".join(page.visible_text.split())
    return Weekly6Visibility.BODY_VISIBLE if "Weekly 6" in normalized else Weekly6Visibility.BODY_NOT_VISIBLE


def parse_visible_weekly6(page: RenderedPage) -> VisibleWeekly6Round:
    lines = [line.strip() for line in page.visible_text.splitlines() if line.strip()]
    fixtures: list[VisibleWeekly6Fixture] = []
    index = 0
    while index < len(lines):
        pick = PICK.match(lines[index])
        if pick is None:
            index += 1
            continue
        if index + 4 >= len(lines) or STARTS_AT.fullmatch(lines[index + 1]) is None:
            raise ValueError("Weekly 6 후보 경기의 화면 표시 형식을 확인할 수 없습니다")
        fixtures.append(VisibleWeekly6Fixture(
            ordinal=int(pick["ordinal"]),
            starts_at=datetime.strptime(lines[index + 1], "%Y.%m.%d %H:%M").replace(tzinfo=KST),
            venue=lines[index + 2], first_team_name=lines[index + 3], second_team_name=lines[index + 4],
        ))
        index += 5
    if not fixtures:
        raise ValueError("Weekly 6 후보 경기가 화면에 표시되지 않았습니다")
    selection = SELECTION_COUNT.search(" ".join(lines))
    starts = sorted(item.starts_at for item in fixtures)
    return VisibleWeekly6Round(
        week_label=f"{starts[0].date().isoformat()}~{starts[-1].date().isoformat()}",
        selection_count=int(selection["count"]) if selection else None,
        fixtures=tuple(sorted(fixtures, key=lambda item: item.ordinal)),
    )


def collect_weekly6_page(session, page: RenderedPage) -> tuple[Weekly6Visibility, int]:
    visibility = inspect_weekly6_page(page)
    if visibility is Weekly6Visibility.BODY_NOT_VISIBLE:
        collect_rendered_page(session, page, "Weekly 6 본문 미표시; 문제 미등록 또는 렌더링 실패를 구분할 수 없어 문제를 저장하지 않음")
        return visibility, 0, 0
    round_data = parse_visible_weekly6(page)
    collect_rendered_page(session, page, f"visible Weekly 6 candidates={len(round_data.fixtures)}", commit=False)
    round_ = session.scalar(select(Weekly6Round).where(Weekly6Round.week_label == round_data.week_label))
    if round_ is None:
        round_ = Weekly6Round(
            official_id=None, week_label=round_data.week_label, opens_at=None, closes_at=None,
            selection_count=round_data.selection_count, source_url=page.url,
            raw_payload={"week_label_source": "candidate_date_range"},
        )
        session.add(round_)
        session.flush()
    else:
        round_.selection_count = round_data.selection_count
        round_.source_url = page.url
    for fixture in round_data.fixtures:
        stored = session.scalar(select(Weekly6VisibleFixture).where(
            Weekly6VisibleFixture.round_id == round_.id,
            Weekly6VisibleFixture.ordinal == fixture.ordinal,
        ))
        fields = {
            "starts_at": fixture.starts_at, "venue": fixture.venue,
            "first_team_name": fixture.first_team_name, "second_team_name": fixture.second_team_name,
            "source_url": page.url, "observed_at": page.fetched_at,
        }
        if stored is None:
            session.add(Weekly6VisibleFixture(round_id=round_.id, ordinal=fixture.ordinal, **fields))
        else:
            for name, value in fields.items():
                setattr(stored, name, value)
    session.commit()
    linked = link_weekly6_schedule_games(session)
    return visibility, len(round_data.fixtures), linked
