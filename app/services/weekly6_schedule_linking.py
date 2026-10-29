"""Link equivalent games that are visibly listed on Weekly 6 and schedule pages."""
import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import VisibleScheduleGame, Weekly6ScheduleLink, Weekly6VisibleFixture

MATCHING_METHOD = "same-start-venue-team-label-containment-v1"


def find_visible_schedule_match(
    fixture: Weekly6VisibleFixture, games: list[VisibleScheduleGame],
) -> VisibleScheduleGame | None:
    matches = [
        game for game in games
        if _same_instant(fixture.starts_at, game.starts_at)
        and _normalized(fixture.venue) == _normalized(game.venue)
        and _teams_match(fixture, game)
    ]
    return matches[0] if len(matches) == 1 else None


def link_weekly6_schedule_games(session: Session) -> int:
    fixtures = list(session.scalars(select(Weekly6VisibleFixture)))
    games = list(session.scalars(select(VisibleScheduleGame)))
    linked = 0
    for fixture in fixtures:
        game = find_visible_schedule_match(fixture, games)
        if game is None:
            continue
        link = session.scalar(select(Weekly6ScheduleLink).where(
            Weekly6ScheduleLink.weekly6_fixture_id == fixture.id,
        ))
        if link is None:
            existing_game_link = session.scalar(select(Weekly6ScheduleLink).where(
                Weekly6ScheduleLink.schedule_game_id == game.id,
            ))
            if existing_game_link is not None:
                continue
            session.add(Weekly6ScheduleLink(
                weekly6_fixture_id=fixture.id, schedule_game_id=game.id,
                matching_method=MATCHING_METHOD, linked_at=datetime.now(UTC),
            ))
            linked += 1
    session.commit()
    return linked


def _teams_match(fixture: Weekly6VisibleFixture, game: VisibleScheduleGame) -> bool:
    fixture_teams = (_normalized(fixture.first_team_name), _normalized(fixture.second_team_name))
    game_teams = (_normalized(game.first_team_name), _normalized(game.second_team_name))
    return all(any(_labels_equivalent(team, candidate) for candidate in game_teams) for team in fixture_teams)


def _labels_equivalent(first: str, second: str) -> bool:
    return first in second or second in first


def _normalized(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def _same_instant(first: datetime, second: datetime) -> bool:
    return first.replace(tzinfo=None) == second.replace(tzinfo=None)
