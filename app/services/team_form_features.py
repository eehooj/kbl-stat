"""Derive prediction features from completed games observed before a cutoff time."""
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Season, TeamFormSnapshot, VisibleScheduleGame

KST = ZoneInfo("Asia/Seoul")
CALCULATION_VERSION = "visible-schedule-v1"


@dataclass(frozen=True)
class TeamForm:
    team_name: str
    games_played: int
    wins: int
    losses: int
    recent_five_wins: int
    recent_five_losses: int
    recent_ten_wins: int
    recent_ten_losses: int
    average_points_for: float
    average_points_against: float
    rest_days: int | None


def parse_as_of(value: str | None) -> datetime:
    if value is None:
        return datetime.now(KST)
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=KST) if parsed.tzinfo is None else parsed.astimezone(KST)


def calculate_team_forms(games: list[VisibleScheduleGame], as_of: datetime) -> list[TeamForm]:
    """Use only completed games strictly before ``as_of`` to avoid future-result leakage."""
    histories: dict[str, list[tuple[datetime, int, int]]] = {}
    for game in games:
        starts_at = _as_kst(game.starts_at)
        if game.status != "final" or starts_at >= as_of or game.first_score is None or game.second_score is None:
            continue
        histories.setdefault(game.first_team_name, []).append((starts_at, game.first_score, game.second_score))
        histories.setdefault(game.second_team_name, []).append((starts_at, game.second_score, game.first_score))

    forms: list[TeamForm] = []
    for team_name, history in histories.items():
        history.sort(key=lambda item: item[0])
        wins = sum(points_for > points_against for _, points_for, points_against in history)
        last_five = history[-5:]
        last_ten = history[-10:]
        rest_days = max((as_of.date() - history[-1][0].date()).days - 1, 0)
        forms.append(TeamForm(
            team_name=team_name, games_played=len(history), wins=wins, losses=len(history) - wins,
            recent_five_wins=_wins(last_five), recent_five_losses=len(last_five) - _wins(last_five),
            recent_ten_wins=_wins(last_ten), recent_ten_losses=len(last_ten) - _wins(last_ten),
            average_points_for=sum(item[1] for item in history) / len(history),
            average_points_against=sum(item[2] for item in history) / len(history), rest_days=rest_days,
        ))
    return sorted(forms, key=lambda form: form.team_name)


def compute_and_store_team_forms(session: Session, season_name: str, as_of: datetime) -> list[TeamForm]:
    season = session.scalar(select(Season).where(Season.name == season_name))
    if season is None:
        raise ValueError(f"저장된 시즌이 없습니다: {season_name}")
    games = list(session.scalars(select(VisibleScheduleGame).where(VisibleScheduleGame.season_id == season.id)))
    forms = calculate_team_forms(games, as_of)
    for form in forms:
        snapshot = session.scalar(select(TeamFormSnapshot).where(
            TeamFormSnapshot.season_id == season.id,
            TeamFormSnapshot.team_name == form.team_name,
            TeamFormSnapshot.as_of == as_of,
        ))
        fields = {
            "games_played": form.games_played, "wins": form.wins, "losses": form.losses,
            "recent_five_wins": form.recent_five_wins, "recent_five_losses": form.recent_five_losses,
            "recent_ten_wins": form.recent_ten_wins, "recent_ten_losses": form.recent_ten_losses,
            "average_points_for": form.average_points_for,
            "average_points_against": form.average_points_against, "rest_days": form.rest_days,
            "calculation_version": CALCULATION_VERSION, "calculated_at": datetime.now(UTC),
        }
        if snapshot is None:
            session.add(TeamFormSnapshot(season_id=season.id, team_name=form.team_name, as_of=as_of, **fields))
        else:
            for name, value in fields.items():
                setattr(snapshot, name, value)
    session.commit()
    return forms


def _as_kst(value: datetime) -> datetime:
    return value.replace(tzinfo=KST) if value.tzinfo is None else value.astimezone(KST)


def _wins(history: list[tuple[datetime, int, int]]) -> int:
    return sum(points_for > points_against for _, points_for, points_against in history)
