"""Collect visible StatsKing game cards without inferring hidden player questions."""
import re
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import RenderedPage
from app.models import StatsKingVisibleGame
from app.services.visible_record_collection import collect_rendered_page

KST = ZoneInfo("Asia/Seoul")
DATE = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")
TIME = re.compile(r"^\d{2}:\d{2}$")
DATE_TIME = re.compile(r"^(?P<date>\d{4}\.\d{2}\.\d{2}) (?P<time>\d{2}:\d{2})$")
PICK = re.compile(r"^Pick \d+$")
DEADLINE = re.compile(r"^게임 마감까지 .+남았습니다\.$")


@dataclass(frozen=True)
class VisibleStatsKingGame:
    starts_at: datetime
    venue: str
    first_team_name: str
    second_team_name: str
    participation_status: str
    deadline_text: str | None


def parse_visible_stats_king_game(page: RenderedPage) -> VisibleStatsKingGame | None:
    """Parse the current game card only when every card field is visibly present."""
    lines = [line.strip() for line in page.visible_text.splitlines() if line.strip()]
    date = next((line for line in lines if DATE.fullmatch(line)), None)
    if date is None or "내 선택 보기" not in lines:
        return None
    index = lines.index("내 선택 보기")
    if index + 6 >= len(lines) or TIME.fullmatch(lines[index + 2]) is None:
        return None
    deadline_text = lines[index + 4] if DEADLINE.fullmatch(lines[index + 4]) else None
    if deadline_text is None:
        return None
    starts_at = datetime.strptime(f"{date} {lines[index + 2]}", "%Y.%m.%d %H:%M").replace(tzinfo=KST)
    return VisibleStatsKingGame(
        starts_at=starts_at,
        participation_status=lines[index + 1],
        venue=lines[index + 3],
        deadline_text=deadline_text,
        first_team_name=lines[index + 5],
        second_team_name=lines[index + 6],
    )


def parse_visible_stats_king_games(page: RenderedPage) -> list[VisibleStatsKingGame]:
    """Parse every complete Pick card visibly rendered in the current weekly board."""
    lines = [line.strip() for line in page.visible_text.splitlines() if line.strip()]
    date_label = next((line for line in lines if DATE.fullmatch(line)), None)
    if date_label is not None and "내 선택 보기" in lines:
        start = lines.index("내 선택 보기") + 1
        end = lines.index("팀 순위", start) if "팀 순위" in lines[start:] else len(lines)
        current_games: list[VisibleStatsKingGame] = []
        for index in range(start, end):
            if not TIME.fullmatch(lines[index]) or index + 4 >= end:
                continue
            deadline_text = lines[index + 2] if DEADLINE.fullmatch(lines[index + 2]) else None
            if deadline_text is None:
                continue
            current_games.append(VisibleStatsKingGame(
                starts_at=datetime.strptime(f"{date_label} {lines[index]}", "%Y.%m.%d %H:%M").replace(tzinfo=KST),
                participation_status=lines[index - 1], venue=lines[index + 1], deadline_text=deadline_text,
                first_team_name=lines[index + 3], second_team_name=lines[index + 4],
            ))
        if current_games:
            return current_games
    participation_status = "마감" if "게임이 마감되었습니다." in lines else "표시됨"
    games: list[VisibleStatsKingGame] = []
    for index, line in enumerate(lines):
        if not PICK.fullmatch(line) or index + 4 >= len(lines):
            continue
        date_time = DATE_TIME.fullmatch(lines[index + 1])
        if date_time is None:
            continue
        starts_at = datetime.strptime(
            f"{date_time['date']} {date_time['time']}", "%Y.%m.%d %H:%M",
        ).replace(tzinfo=KST)
        games.append(VisibleStatsKingGame(
            starts_at=starts_at,
            venue=lines[index + 2],
            first_team_name=lines[index + 3],
            second_team_name=lines[index + 4],
            participation_status=participation_status,
            deadline_text=None,
        ))
    if games:
        return games
    legacy = parse_visible_stats_king_game(page)
    return [legacy] if legacy is not None else []


def collect_visible_stats_king_game(session: Session, page: RenderedPage) -> VisibleStatsKingGame | None:
    game = parse_visible_stats_king_game(page)
    detail = "StatsKing visible game card unavailable" if game is None else "StatsKing visible game card=1"
    collect_rendered_page(session, page, detail, commit=False)
    if game is None:
        session.commit()
        return None
    key_source = f"{game.starts_at.isoformat()}|{game.venue}|{game.first_team_name}|{game.second_team_name}"
    observed_key = sha256(key_source.encode("utf-8")).hexdigest()
    stored = session.scalar(select(StatsKingVisibleGame).where(StatsKingVisibleGame.observed_key == observed_key))
    fields = {
        "starts_at": game.starts_at,
        "venue": game.venue,
        "first_team_name": game.first_team_name,
        "second_team_name": game.second_team_name,
        "participation_status": game.participation_status,
        "deadline_text": game.deadline_text,
        "source_url": page.url,
        "observed_at": page.fetched_at,
    }
    if stored is None:
        session.add(StatsKingVisibleGame(observed_key=observed_key, **fields))
    else:
        for name, value in fields.items():
            setattr(stored, name, value)
    session.commit()
    return game


def collect_visible_stats_king_games(session: Session, page: RenderedPage) -> list[VisibleStatsKingGame]:
    games = parse_visible_stats_king_games(page)
    collect_rendered_page(session, page, f"StatsKing visible game cards={len(games)}", commit=False)
    for game in games:
        key_source = f"{game.starts_at.isoformat()}|{game.venue}|{game.first_team_name}|{game.second_team_name}"
        observed_key = sha256(key_source.encode("utf-8")).hexdigest()
        stored = session.scalar(select(StatsKingVisibleGame).where(StatsKingVisibleGame.observed_key == observed_key))
        fields = {
            "starts_at": game.starts_at, "venue": game.venue,
            "first_team_name": game.first_team_name, "second_team_name": game.second_team_name,
            "participation_status": game.participation_status, "deadline_text": game.deadline_text,
            "source_url": page.url, "observed_at": page.fetched_at,
        }
        if stored is None:
            session.add(StatsKingVisibleGame(observed_key=observed_key, **fields))
        else:
            for name, value in fields.items():
                setattr(stored, name, value)
    session.commit()
    return games
