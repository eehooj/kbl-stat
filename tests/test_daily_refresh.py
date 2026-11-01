from app.services.daily_refresh import run_daily_refresh_steps


def test_retries_only_the_failed_step_and_continues() -> None:
    calls = {"stable": 0, "flaky": 0, "after": 0}

    def stable() -> None:
        calls["stable"] += 1

    def flaky() -> None:
        calls["flaky"] += 1
        if calls["flaky"] == 1:
            raise RuntimeError("temporary browser failure")

    def after() -> None:
        calls["after"] += 1

    results = run_daily_refresh_steps(
        [("stable", stable), ("flaky", flaky), ("after", after)],
        max_attempts=2, retry_delay_seconds=0,
    )
    assert calls == {"stable": 1, "flaky": 2, "after": 1}
    assert [(result.name, result.attempts, result.succeeded) for result in results] == [
        ("stable", 1, True), ("flaky", 2, True), ("after", 1, True),
    ]


def test_reports_final_failure_without_skipping_later_steps() -> None:
    later_calls = 0

    def broken() -> None:
        raise ValueError("still broken")

    def later() -> None:
        nonlocal later_calls
        later_calls += 1

    results = run_daily_refresh_steps(
        [("broken", broken), ("later", later)], max_attempts=2, retry_delay_seconds=0,
    )
    assert results[0].succeeded is False
    assert results[0].attempts == 2
    assert results[0].error == "still broken"
    assert results[1].succeeded is True
    assert later_calls == 1
