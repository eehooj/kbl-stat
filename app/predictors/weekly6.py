from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class TeamForm:
    team_name: str
    season_win_rate: float | None
    recent_5_win_rate: float | None
    recent_10_win_rate: float | None
    home_or_away_win_rate: float | None
    net_rating: float | None
    rest_days: int | None


@dataclass(frozen=True)
class Weekly6Match:
    ordinal: int
    home: TeamForm
    away: TeamForm


@dataclass(frozen=True)
class MatchRecommendation:
    ordinal: int
    recommended_team: str | None
    home_win_probability: float | None
    away_win_probability: float | None
    confidence: str
    reasons: tuple[str, ...]
    data_gaps: tuple[str, ...]
    selection_score: float | None


class Weekly6Predictor:
    """Transparent baseline. Probabilities are withheld until calibrated externally."""

    REQUIRED = ("season_win_rate", "recent_5_win_rate", "home_or_away_win_rate")

    def recommend(self, match: Weekly6Match) -> MatchRecommendation:
        gaps = tuple(
            label
            for label in self.REQUIRED
            if getattr(match.home, label) is None or getattr(match.away, label) is None
        )
        if gaps:
            return MatchRecommendation(match.ordinal, None, None, None, "낮음", (), gaps, None)

        home_values = [match.home.season_win_rate, match.home.recent_5_win_rate, match.home.home_or_away_win_rate]
        away_values = [match.away.season_win_rate, match.away.recent_5_win_rate, match.away.home_or_away_win_rate]
        # This ranking score is intentionally not displayed as a probability. It needs backtest calibration.
        home_score, away_score = mean(home_values), mean(away_values)
        winner = match.home.team_name if home_score >= away_score else match.away.team_name
        return MatchRecommendation(
            match.ordinal, winner, None, None, "보통",
            ("시즌 승률, 최근 5경기 승률, 홈/원정 승률의 동일 가중 기준선 비교",), (),
            abs(home_score - away_score),
        )

    def select(self, matches: list[Weekly6Match], selection_count: int) -> list[MatchRecommendation]:
        recommendations = [self.recommend(match) for match in matches]
        usable = [item for item in recommendations if item.recommended_team is not None]
        # Before calibration, strength means score separation only and is not a joint hit probability.
        return sorted(usable, key=lambda item: item.selection_score or 0.0, reverse=True)[:selection_count]
