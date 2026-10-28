from app.predictors.weekly6 import TeamForm, Weekly6Match, Weekly6Predictor


def form(name: str, value: float | None) -> TeamForm:
    return TeamForm(name, value, value, value, value, 0.0, 2)


def test_withholds_recommendation_for_missing_required_data() -> None:
    recommendation = Weekly6Predictor().recommend(Weekly6Match(1, form("홈", None), form("원정", 0.5)))
    assert recommendation.recommended_team is None
    assert recommendation.home_win_probability is None
    assert "season_win_rate" in recommendation.data_gaps
    assert recommendation.selection_score is None


def test_baseline_recommends_better_observed_team_without_uncalibrated_probability() -> None:
    recommendation = Weekly6Predictor().recommend(Weekly6Match(1, form("홈", 0.7), form("원정", 0.4)))
    assert recommendation.recommended_team == "홈"
    assert recommendation.home_win_probability is None
    assert recommendation.confidence == "보통"
