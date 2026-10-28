"""Persist only facts visible in KBL's rendered season-leader page."""
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import RenderedPage
from app.models import CollectionLog, RawSourceDocument, Season, SeasonPlayerStat

TEAM_NAMES = (
    "대구 한국가스공사", "울산 현대모비스", "안양 정관장", "부산 KCC", "서울 삼성",
    "고양 소노", "서울 SK", "창원 LG", "수원 KT", "원주 DB",
)
METRICS = {
    "득점", "리바운드", "어시스트", "스틸", "블록", "3점슛", "3점슛 성공률", "자유투 성공률", "야투 성공률",
    "PER", "OFFRTG", "DEFRTG", "NETRTG", "EFG%", "TS%", "AST%", "AST/TO", "AST Ratio",
    "OREB%", "DREB%", "REB%", "USG%", "PACE", "TO RATIO", "PIE", "POSS",
}
ROW = re.compile(
    rf"^(?P<rank>\d+)\s+(?P<name>.+?)\s+(?P<team>{'|'.join(map(re.escape, TEAM_NAMES))})\s+(?P<value>-?\d+(?:\.\d+)?)$"
)


@dataclass(frozen=True)
class VisibleLeader:
    metric: str
    rank: int
    player_name: str
    team_name: str
    value: float


def parse_season_leaders(visible_text: str) -> tuple[str, list[VisibleLeader]]:
    seasons = re.findall(r"20\d{2}-20\d{2}", visible_text)
    if not seasons:
        raise ValueError("Rendered page did not display a season label")
    lines = [item.strip() for item in visible_text.splitlines() if item.strip()]
    metric: str | None = None
    leaders: list[VisibleLeader] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line in METRICS:
            metric = line
            index += 1
            continue
        if metric is None:
            index += 1
            continue
        match = ROW.match(line)
        if match:
            leaders.append(VisibleLeader(
                metric=metric, rank=int(match["rank"]), player_name=match["name"],
                team_name=match["team"], value=float(match["value"]),
            ))
            index += 1
            continue
        # Chromium's rendered text exposes each cell on its own line.
        if line.isdigit() and index + 3 < len(lines) and lines[index + 2] in TEAM_NAMES:
            try:
                value = float(lines[index + 3])
            except ValueError:
                index += 1
                continue
            leaders.append(VisibleLeader(
                metric=metric, rank=int(line), player_name=lines[index + 1],
                team_name=lines[index + 2], value=value,
            ))
            index += 4
            continue
        index += 1
    if not leaders:
        raise ValueError("Rendered page had no parseable season-leader rows")
    return seasons[0], leaders


def collect_season_leaders(session: Session, page: RenderedPage) -> int:
    season_name, leaders = parse_season_leaders(page.visible_text)
    season = session.scalar(select(Season).where(Season.name == season_name))
    if season is None:
        season = Season(code=season_name, name=season_name)
        session.add(season)
        session.flush()
    collect_rendered_page(session, page, f"visible season leaders={len(leaders)}", commit=False)
    for leader in leaders:
        value = session.scalar(select(SeasonPlayerStat).where(
            SeasonPlayerStat.season_id == season.id, SeasonPlayerStat.metric == leader.metric,
            SeasonPlayerStat.player_name == leader.player_name, SeasonPlayerStat.team_name == leader.team_name,
        ))
        fields = {"player_name": leader.player_name, "team_name": leader.team_name, "value": leader.value,
                  "source_url": page.url, "observed_at": page.fetched_at}
        if value is None:
            session.add(SeasonPlayerStat(season_id=season.id, metric=leader.metric, rank=leader.rank, **fields))
        else:
            for name, field_value in fields.items():
                setattr(value, name, field_value)
    session.commit()
    return len(leaders)


def collect_rendered_page(session: Session, page: RenderedPage, detail: str, commit: bool = True) -> None:
    """Retain an observable page snapshot without inferring hidden records."""
    session.add(CollectionLog(source_url=page.url, status="rendered", fetched_at=page.fetched_at,
                              response_sha256=page.content_hash, detail=detail))
    if session.scalar(select(RawSourceDocument).where(RawSourceDocument.content_hash == page.content_hash)) is None:
        session.add(RawSourceDocument(source_url=page.url, fetched_at=page.fetched_at,
                                      content_hash=page.content_hash, content_type="application/json", body=page.body))
    if commit:
        session.commit()
