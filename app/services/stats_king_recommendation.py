"""Recommend public-record leaders for the two teams on the visible StatsKing game card."""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    PlayerAvailability,
    StatsKingVisibleGame,
    VisiblePlayerGameStat,
    VisiblePlayerSeasonStat,
    VisibleScheduleGame,
)

METRICS = (
    ("득점", "points"),
    ("리바운드", "rebounds"),
    ("어시스트", "assists"),
)


@dataclass(frozen=True)
class StatsKingLeader:
    metric_label: str
    player_name: str
    team_name: str
    total: int
    games_played: int
    per_game: float
    recent_games: int
    recent_per_game: float | None
    ranking_per_game: float


@dataclass(frozen=True)
class StatsKingRecommendation:
    game: StatsKingVisibleGame
    leaders: list[StatsKingLeader]
    unavailable_players: list[str]


def recommend_stats_king_leaders(session: Session) -> StatsKingRecommendation | None:
    game = session.scalar(select(StatsKingVisibleGame).order_by(StatsKingVisibleGame.observed_at.desc()))
    if game is None:
        return None
    availability = list(session.scalars(select(PlayerAvailability).where(
        PlayerAvailability.availability_date == game.starts_at.date(),
        PlayerAvailability.status == "out",
    )))
    players = list(session.scalars(select(VisiblePlayerSeasonStat).order_by(
        VisiblePlayerSeasonStat.observed_at.desc(),
    )))
    candidates = [
        player for player in players
        if _same_team(player.team_name, game.first_team_name) or _same_team(player.team_name, game.second_team_name)
        if not _is_unavailable(player, availability)
    ]
    unavailable_players = [
        item.player_name for item in availability
        if item.team_name is None
        or _same_team(item.team_name, game.first_team_name)
        or _same_team(item.team_name, game.second_team_name)
    ]
    if not candidates:
        return StatsKingRecommendation(game=game, leaders=[], unavailable_players=unavailable_players)
    recent_forms = _recent_forms(session, game, candidates)
    leaders = [_leader(metric_label, field, candidates, recent_forms) for metric_label, field in METRICS]
    return StatsKingRecommendation(game=game, leaders=leaders, unavailable_players=unavailable_players)


def render_stats_king_recommendation(
    result: StatsKingRecommendation | None,
) -> str:
    if result is None:
        return "KBL STATSKING RECOMMENDATION\n\n확인된 StatsKing 경기 카드가 없습니다. collect-stats-king을 먼저 실행하세요."
    game, leaders = result.game, result.leaders
    header = "KBL STATSKING RECOMMENDATION"
    matchup = f"경기: {game.first_team_name} vs {game.second_team_name} ({game.starts_at.isoformat()})"
    if not leaders:
        return f"{header}\n\n{matchup}\n\n두 팀의 공개 선수 기록이 없어 추천을 만들지 않았습니다."
    lines = [header, matchup, "공개 시즌 평균과 확인 가능한 최근 폼 기준 추천 (공식 선택지·확률은 미확인):"]
    if result.unavailable_players:
        lines.append(f"확인된 결장 제외: {', '.join(result.unavailable_players)}")
    for leader in leaders:
        lines.append(
            f"{leader.metric_label}: {leader.player_name} ({leader.team_name}) - "
            f"시즌 {leader.per_game:.2f}/경기, 최근 {leader.recent_games}경기 "
            f"{leader.recent_per_game:.2f}/경기" if leader.recent_per_game is not None
            else f"{leader.metric_label}: {leader.player_name} ({leader.team_name}) - "
            f"시즌 {leader.per_game:.2f}/경기, 최근 데이터 부족"
        )
    return "\n".join(lines)


def _leader(
    metric_label: str,
    field: str,
    candidates: list[VisiblePlayerSeasonStat],
    recent_forms: dict[tuple[str, str], tuple[int, dict[str, float]]],
) -> StatsKingLeader:
    eligible = [player for player in candidates if player.games_played > 0]
    if not eligible:
        raise ValueError("경기 수가 있는 공개 선수 기록이 없습니다")
    selected = max(
        eligible,
        key=lambda player: (_ranking_per_game(player, field, recent_forms), getattr(player, field), player.player_name),
    )
    total = getattr(selected, field)
    recent_games, metrics = recent_forms.get((selected.player_name, selected.team_name), (0, {}))
    return StatsKingLeader(
        metric_label=metric_label,
        player_name=selected.player_name,
        team_name=selected.team_name,
        total=total,
        games_played=selected.games_played,
        per_game=total / selected.games_played,
        recent_games=recent_games,
        recent_per_game=metrics.get(field),
        ranking_per_game=_ranking_per_game(selected, field, recent_forms),
    )


def _recent_forms(
    session: Session, game: StatsKingVisibleGame, candidates: list[VisiblePlayerSeasonStat],
) -> dict[tuple[str, str], tuple[int, dict[str, float]]]:
    allowed = {(player.player_name, player.team_name) for player in candidates}
    observed = session.execute(
        select(VisiblePlayerGameStat, VisibleScheduleGame.starts_at)
        .join(VisibleScheduleGame, VisibleScheduleGame.id == VisiblePlayerGameStat.schedule_game_id)
        .where(VisibleScheduleGame.starts_at < game.starts_at)
        .order_by(VisibleScheduleGame.starts_at.desc())
    ).all()
    grouped: dict[tuple[str, str], list[VisiblePlayerGameStat]] = {}
    for stat, _starts_at in observed:
        key = next((key for key in allowed if _same_team(key[0], stat.player_name) and _same_team(key[1], stat.team_name)), None)
        if key is not None and len(grouped.setdefault(key, [])) < 5:
            grouped[key].append(stat)
    return {
        key: (len(rows), {
            "points": sum(row.points for row in rows) / len(rows),
            "rebounds": sum(row.rebounds for row in rows) / len(rows),
            "assists": sum(row.assists for row in rows) / len(rows),
        })
        for key, rows in grouped.items()
        if len(rows) >= 3
    }


def _ranking_per_game(
    player: VisiblePlayerSeasonStat,
    field: str,
    recent_forms: dict[tuple[str, str], tuple[int, dict[str, float]]],
) -> float:
    season_per_game = getattr(player, field) / player.games_played
    recent_games, metrics = recent_forms.get((player.player_name, player.team_name), (0, {}))
    if recent_games < 3 or field not in metrics:
        return season_per_game
    return (metrics[field] * 0.6) + (season_per_game * 0.4)


def _same_team(first: str, second: str) -> bool:
    return "".join(first.split()).casefold() == "".join(second.split()).casefold()


def _is_unavailable(player: VisiblePlayerSeasonStat, availability: list[PlayerAvailability]) -> bool:
    return any(
        _same_team(player.player_name, item.player_name)
        and _is_game_team(item.team_name, player.team_name)
        for item in availability
    )


def _is_game_team(availability_team: str | None, team_name: str) -> bool:
    return availability_team is None or _same_team(availability_team, team_name)
