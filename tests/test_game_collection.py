from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.collectors.official_pages import OfficialPage
from app.database import Base
from app.models import Game, PlayerGameStat, TeamGameStat
from app.services.game_collection import collect_game_stats, collect_schedule


def page(name: str) -> OfficialPage:
    return OfficialPage(f"https://api.kbl.or.kr/{name}", datetime.now(UTC), "{}", name.ljust(64, "0"))


class FakeKBLClient:
    def __init__(self) -> None:
        self.schedule = {
            "gmkey": "S49G01N1", "seasonCode": 49, "seasonName1": "2026-2027", "gameDate": "20261003",
            "gameStart": "1400", "tcodeH": "60", "tcodeA": "50", "tnameH": "부산 KCC", "tnameA": "창원 LG",
            "scoreH": 68, "scoreA": 103, "isStarted": 1, "isEnded": 1,
        }

    def list_matches(self, _from_date: str, _to_date: str):
        return page("match-list"), [self.schedule]

    def get_match(self, _game_key: str):
        return page("match-detail"), {"game": self.schedule}

    def get_team_records(self, _game_key: str):
        return page("team-record"), [
            {"tcode": "60", "records": {"score": 68, "ast": 15}},
            {"tcode": "50", "records": {"score": 103, "ast": 27}},
        ]

    def get_player_stats(self, _game_key: str):
        return page("player-stat"), [{
            "player": {"pcode": "123", "pname": "선수", "tcode": "60"},
            "records": {"score": 10, "playMin": 20, "playSec": 0}, "startFlag": 1,
        }]


def test_schedule_is_idempotent_and_box_scores_are_upserted() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    client = FakeKBLClient()
    with Session(engine) as session:
        assert collect_schedule(session, client, "20261001", "20261031") == 1
        assert collect_schedule(session, client, "20261001", "20261031") == 1
        game = session.scalar(select(Game))
        assert game.official_id == "S49G01N1"
        assert game.status == "completed"
        collect_game_stats(session, client, game)
        assert len(session.scalars(select(TeamGameStat)).all()) == 2
        assert len(session.scalars(select(PlayerGameStat)).all()) == 1
