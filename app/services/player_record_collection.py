"""Store public player record-table values that are visibly rendered by KBL."""
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import RenderedPlayerRecordPage
from app.models import Season, VisiblePlayerSeasonStat
from app.services.visible_record_collection import collect_rendered_page

TEAM_NAME_BY_EMBLEM = {
    "db": "원주 DB",
    "hd": "울산 현대모비스",
    "kcc": "부산 KCC",
    "kgc": "안양 정관장",
    "kt": "수원 KT",
    "lg": "창원 LG",
    "pega": "대구 한국가스공사",
    "sono": "고양 소노",
    "ss": "서울 삼성",
    "sk": "서울 SK",
}


def collect_visible_player_records(session: Session, pages: list[RenderedPlayerRecordPage]) -> int:
    if not pages:
        raise ValueError("선수 기록 화면이 없습니다")
    season_name = _season_from_page(pages[0])
    season = session.scalar(select(Season).where(Season.name == season_name))
    if season is None:
        season = Season(code=season_name, name=season_name)
        session.add(season)
        session.flush()
    count = 0
    for rendered in pages:
        if _season_from_page(rendered) != season_name:
            raise ValueError("선수 기록 화면 사이에 시즌이 바뀌었습니다")
        collect_rendered_page(session, rendered.page, f"visible player season records={len(rendered.rows)}", commit=False)
        for row in rendered.rows:
            team_name = TEAM_NAME_BY_EMBLEM.get(row.team_emblem_code)
            if team_name is None:
                raise ValueError(f"확인되지 않은 화면상 팀 엠블럼 코드: {row.team_emblem_code}")
            stored = session.scalar(select(VisiblePlayerSeasonStat).where(
                VisiblePlayerSeasonStat.season_id == season.id,
                VisiblePlayerSeasonStat.player_name == row.player_name,
                VisiblePlayerSeasonStat.team_name == team_name,
            ))
            fields = {
                "games_played": row.games_played,
                "points": row.points,
                "rebounds": row.rebounds,
                "assists": row.assists,
                "source_url": rendered.page.url,
                "observed_at": rendered.page.fetched_at,
            }
            if stored is None:
                session.add(VisiblePlayerSeasonStat(
                    season_id=season.id, player_name=row.player_name, team_name=team_name, **fields,
                ))
            else:
                for name, value in fields.items():
                    setattr(stored, name, value)
            count += 1
    session.commit()
    return count


def _season_from_page(rendered: RenderedPlayerRecordPage) -> str:
    match = re.search(r"20\d{2}-20\d{2}", rendered.page.visible_text)
    if match is None:
        raise ValueError("선수 기록 화면에 시즌이 표시되지 않았습니다")
    return match.group(0)
