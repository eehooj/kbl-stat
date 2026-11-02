import pytest

from app.services.stats_king_research import shrink_average


def test_small_samples_are_pulled_more_towards_prior():
    assert shrink_average(15, 1, 5) == 7.5
    assert shrink_average(150, 10, 5) > shrink_average(15, 1, 5)
    assert shrink_average(15, 1, 5, 0) == 15


def test_rejects_no_observed_games():
    with pytest.raises(ValueError):
        shrink_average(0, 0, 5)
