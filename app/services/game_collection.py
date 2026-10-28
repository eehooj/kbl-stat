"""Incremental persistence for verified KBL schedule and box-score responses."""
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.official_pages import KBLApiClient, OfficialPage
from app.models import (
    CollectionLog,
    Game,
    Player,
    PlayerGameStat,
    RawSourceDocument,
    Season,
    Team,
    TeamGameStat,
)

SEOUL = ZoneInfo("Asia/Seoul")


def _record_source(session: Session, page: OfficialPage, status: str, detail: str) -> None:
    session.add(CollectionLog(source_url=page.url, status=status, fetched_at=page.fetched_at,
                              response_sha256=page.content_hash, detail=detail))
    if session.scalar(select(RawSourceDocument).where(RawSourceDocument.content_hash == page.content_hash)) is None:
        session.add(RawSourceDocument(source_url=page.url, fetched_at=page.fetched_at,
                                      content_hash=page.content_hash, content_type="application/json", body=page.body))


def _team(session: Session, code: str, name: str | None = None) -> Team:
    value = session.scalar(select(Team).where(Team.official_id == code))
    if value is None:
        if name is None:
            raise ValueError(f"Unknown KBL team code {code}")
        value = Team(official_id=code, name=name)
        session.add(value)
        session.flush()
    elif name and value.name != name:
        value.name = name
    return value


def _season(session: Session, item: dict[str, Any]) -> Season:
    code = str(item["seasonCode"])
    value = session.scalar(select(Season).where(Season.code == code))
    if value is None:
        value = Season(code=code, name=item.get("seasonName1") or item.get("seasonName"))
        session.add(value)
        session.flush()
    return value


def _starts_at(item: dict[str, Any]) -> datetime | None:
    if not item.get("gameDate") or not item.get("gameStart"):
        return None
    return datetime.strptime(f"{item['gameDate']}{str(item['gameStart']).zfill(4)}", "%Y%m%d%H%M").replace(tzinfo=SEOUL)


def _status(item: dict[str, Any]) -> str:
    return "completed" if item.get("isEnded") == 1 else "in_progress" if item.get("isStarted") == 1 else "scheduled"


def upsert_schedule_item(session: Session, item: dict[str, Any], page: OfficialPage) -> Game:
    required = ("gmkey", "seasonCode", "tcodeH", "tcodeA", "tnameH", "tnameA")
    missing = [key for key in required if key not in item]
    if missing:
        raise ValueError(f"KBL schedule item missing: {', '.join(missing)}")
    season = _season(session, item)
    home, away = _team(session, str(item["tcodeH"]), item["tnameH"]), _team(session, str(item["tcodeA"]), item["tnameA"])
    value = session.scalar(select(Game).where(Game.season_id == season.id, Game.official_id == item["gmkey"]))
    fields = {"starts_at": _starts_at(item), "home_team_id": home.id, "away_team_id": away.id,
              "home_score": item.get("scoreH"), "away_score": item.get("scoreA"), "status": _status(item),
              "source_url": page.url, "fetched_at": page.fetched_at}
    if value is None:
        value = Game(official_id=item["gmkey"], season_id=season.id, **fields)
        session.add(value)
        session.flush()
    else:
        for name, field_value in fields.items():
            setattr(value, name, field_value)
    return value


def collect_schedule(session: Session, client: KBLApiClient, from_date: str, to_date: str) -> int:
    page, items = client.list_matches(from_date, to_date)
    _record_source(session, page, "parsed", f"schedule range={from_date}..{to_date}, matches={len(items)}")
    for item in items:
        upsert_schedule_item(session, item, page)
    session.commit()
    return len(items)


def _upsert_player(session: Session, raw: dict[str, Any], team_id: int) -> Player:
    value = session.scalar(select(Player).where(Player.official_id == str(raw["pcode"])))
    if value is None:
        value = Player(official_id=str(raw["pcode"]), name=raw["pname"], team_id=team_id)
        session.add(value)
        session.flush()
    else:
        value.name, value.team_id = raw["pname"], team_id
    return value


def collect_game_stats(session: Session, client: KBLApiClient, game: Game) -> None:
    detail_page, detail = client.get_match(game.official_id)
    _record_source(session, detail_page, "parsed", f"match detail game_key={game.official_id}")
    game = upsert_schedule_item(session, detail["game"], detail_page)
    if game.status != "completed":
        session.commit()
        return
    team_page, team_rows = client.get_team_records(game.official_id)
    _record_source(session, team_page, "parsed", f"team records game_key={game.official_id}")
    for row in team_rows:
        team = _team(session, str(row["tcode"]))
        value = session.scalar(select(TeamGameStat).where(TeamGameStat.game_id == game.id, TeamGameStat.team_id == team.id))
        if value is None:
            session.add(TeamGameStat(game_id=game.id, team_id=team.id, stats=row["records"], source_updated_at=team_page.fetched_at))
        else:
            value.stats, value.source_updated_at = row["records"], team_page.fetched_at
    player_page, player_rows = client.get_player_stats(game.official_id)
    _record_source(session, player_page, "parsed", f"player stats game_key={game.official_id}")
    for row in player_rows:
        team = _team(session, str(row["player"]["tcode"]))
        player = _upsert_player(session, row["player"], team.id)
        value = session.scalar(select(PlayerGameStat).where(PlayerGameStat.game_id == game.id, PlayerGameStat.player_id == player.id))
        played = bool(row["records"].get("playMin") or row["records"].get("playSec"))
        if value is None:
            session.add(PlayerGameStat(game_id=game.id, player_id=player.id, played=played, stats=row["records"]))
        else:
            value.played, value.stats = played, row["records"]
    session.commit()


def collect_completed_game_stats(session: Session, client: KBLApiClient, limit: int | None = None) -> int:
    statement = select(Game).where(Game.status == "completed").order_by(Game.starts_at)
    if limit is not None:
        statement = statement.limit(limit)
    games = session.scalars(statement).all()
    for game in games:
        collect_game_stats(session, client, game)
    return len(games)
