"""Conservative official-page acquisition.

No private API endpoint is inferred here.  The returned HTML is retained as evidence
and parsing is deliberately separate from acquisition, so selectors can be added only
after a live response is reviewed.
"""
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

import httpx

from app.config import Settings, get_settings

KBL_BASE_URL = "https://www.kbl.or.kr"
SCHEDULE_URL = f"{KBL_BASE_URL}/match/schedule"
CHALLENGE_URLS = {
    "stats_king": f"{KBL_BASE_URL}/game/challenge/stats",
    "daily_picks": f"{KBL_BASE_URL}/game/challenge/daily-picks",
    "weekly6": f"{KBL_BASE_URL}/game/challenge/weekly6",
}


@dataclass(frozen=True)
class OfficialPage:
    url: str
    fetched_at: datetime
    body: str
    content_hash: str


class KBLOfficialPageClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._last_request_at: float | None = None

    def fetch(self, url: str) -> OfficialPage:
        if self._last_request_at is not None:
            remaining = self.settings.kbl_request_delay_seconds - (time.monotonic() - self._last_request_at)
            if remaining > 0:
                time.sleep(remaining)
        with httpx.Client(
            timeout=self.settings.kbl_http_timeout_seconds,
            headers={"User-Agent": self.settings.kbl_user_agent, "Accept": "text/html,application/xhtml+xml"},
            follow_redirects=True,
        ) as client:
            response = client.get(url)
            self._last_request_at = time.monotonic()
            response.raise_for_status()
        return OfficialPage(
            url=str(response.url),
            fetched_at=datetime.now(UTC),
            body=response.text,
            content_hash=sha256(response.content).hexdigest(),
        )

    def fetch_schedule(self) -> OfficialPage:
        return self.fetch(SCHEDULE_URL)

    def fetch_challenge(self, challenge_type: str) -> OfficialPage:
        return self.fetch(CHALLENGE_URLS[challenge_type])
