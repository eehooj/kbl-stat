"""Run bounded, independently retryable steps for the visible-page daily refresh."""
from collections.abc import Callable
from dataclasses import dataclass
from time import sleep


@dataclass(frozen=True)
class RefreshStepResult:
    name: str
    attempts: int
    succeeded: bool
    error: str | None


def run_daily_refresh_steps(
    steps: list[tuple[str, Callable[[], None]]],
    max_attempts: int = 2,
    retry_delay_seconds: float = 1.5,
) -> list[RefreshStepResult]:
    """Run every step, retry failures only, and never loop without a fixed bound."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    if retry_delay_seconds < 0:
        raise ValueError("retry_delay_seconds cannot be negative")
    results: list[RefreshStepResult] = []
    for name, step in steps:
        error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                step()
            # The boundary intentionally isolates browser, parser, and database failures alike.
            except Exception as caught:  # noqa: BLE001
                error = caught
                if attempt < max_attempts and retry_delay_seconds:
                    sleep(retry_delay_seconds)
                continue
            results.append(RefreshStepResult(name, attempt, True, None))
            break
        else:
            results.append(RefreshStepResult(name, max_attempts, False, str(error)))
    return results
