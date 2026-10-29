"""Recommend public-record leaders for the two teams on the visible StatsKing game card."""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import StatsKingVisibleGame, VisiblePlayerSeasonStat

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


def recommend_stats_king_leaders(session: Session) -> tuple[StatsKingVisibleGame, list[StatsKingLeader]] | None:
    game = session.scalar(select(StatsKingVisibleGame).order_by(StatsKingVisibleGame.observed_at.desc()))
    if game is None:
        return None
    players = list(session.scalars(select(VisiblePlayerSeasonStat).order_by(
        VisiblePlayerSeasonStat.observed_at.desc(),
    )))
    candidates = [
        player for player in players
        if _same_team(player.team_name, game.first_team_name) or _same_team(player.team_name, game.second_team_name)
    ]
    if not candidates:
        return game, []
    leaders = [_leader(metric_label, field, candidates) for metric_label, field in METRICS]
    return game, leaders


def render_stats_king_recommendation(
    result: tuple[StatsKingVisibleGame, list[StatsKingLeader]] | None,
) -> str:
    if result is None:
        return "KBL STATSKING RECOMMENDATION\n\n확인된 StatsKing 경기 카드가 없습니다. collect-stats-king을 먼저 실행하세요."
    game, leaders = result
    header = "KBL STATSKING RECOMMENDATION"
    matchup = f"경기: {game.first_team_name} vs {game.second_team_name} ({game.starts_at.isoformat()})"
    if not leaders:
        return f"{header}\n\n{matchup}\n\n두 팀의 공개 선수 기록이 없어 추천을 만들지 않았습니다."
    lines = [header, matchup, "공개 시즌 기록의 경기당 평균 기준 추천 (공식 선택지·확률은 미확인):"]
    for leader in leaders:
        lines.append(
            f"{leader.metric_label}: {leader.player_name} ({leader.team_name}) - "
            f"{leader.per_game:.2f}/경기, 누적 {leader.total}, {leader.games_played}경기"
        )
    return "\n".join(lines)


def _leader(metric_label: str, field: str, candidates: list[VisiblePlayerSeasonStat]) -> StatsKingLeader:
    eligible = [player for player in candidates if player.games_played > 0]
    if not eligible:
        raise ValueError("경기 수가 있는 공개 선수 기록이 없습니다")
    selected = max(
        eligible,
        key=lambda player: (getattr(player, field) / player.games_played, getattr(player, field), player.player_name),
    )
    total = getattr(selected, field)
    return StatsKingLeader(
        metric_label=metric_label,
        player_name=selected.player_name,
        team_name=selected.team_name,
        total=total,
        games_played=selected.games_played,
        per_game=total / selected.games_played,
    )


def _same_team(first: str, second: str) -> bool:
    return "".join(first.split()).casefold() == "".join(second.split()).casefold()
