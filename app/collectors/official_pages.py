"""Conservative official-page acquisition.

No private API endpoint is inferred here.  The returned HTML is retained as evidence
and parsing is deliberately separate from acquisition, so selectors can be added only
after a live response is reviewed.
"""
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from app.config import Settings, get_settings

KBL_BASE_URL = "https://www.kbl.or.kr"
KBL_API_BASE_URL = "https://api.kbl.or.kr"
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


class KBLApiClient:
    """Verified public KBL web API client (contract inspected 2026-10-28)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._last_request_at: float | None = None

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> tuple[OfficialPage, Any]:
        if self._last_request_at is not None:
            remaining = self.settings.kbl_request_delay_seconds - (time.monotonic() - self._last_request_at)
            if remaining > 0:
                time.sleep(remaining)
        headers = {
            "User-Agent": self.settings.kbl_user_agent, "Accept": "application/json",
            "Channel": "WEB", "TeamCode": "XX", "X-Requested-With": "XMLHttpRequest",
            "Cache-Control": "no-cache", "Pragma": "no-cache", "lang": "ko",
        }
        with httpx.Client(timeout=self.settings.kbl_http_timeout_seconds, headers=headers) as client:
            response = client.get(f"{KBL_API_BASE_URL}{path}", params=params)
            self._last_request_at = time.monotonic()
            response.raise_for_status()
        page = OfficialPage(str(response.url), datetime.now(UTC), response.text, sha256(response.content).hexdigest())
        return page, json.loads(page.body)

    def list_matches(self, from_date: str, to_date: str) -> tuple[OfficialPage, list[dict[str, Any]]]:
        page, payload = self._get_json("/match/list", {"fromDate": from_date, "toDate": to_date, "tcodeList": "all"})
        if not isinstance(payload, list):
            raise TypeError(f"Unexpected KBL match-list response: {payload!r}")
        return page, payload

    def get_match(self, game_key: str) -> tuple[OfficialPage, dict[str, Any]]:
        page, payload = self._get_json(f"/match/{game_key}")
        if not isinstance(payload, dict) or "game" not in payload:
            raise ValueError(f"Unexpected KBL match response for {game_key}")
        return page, payload

    def get_team_records(self, game_key: str) -> tuple[OfficialPage, list[dict[str, Any]]]:
        page, payload = self._get_json(f"/match/{game_key}/team-record")
        if not isinstance(payload, list):
            raise TypeError(f"Unexpected KBL team-record response for {game_key}")
        return page, payload

    def get_player_stats(self, game_key: str) -> tuple[OfficialPage, list[dict[str, Any]]]:
        page, payload = self._get_json(f"/match/{game_key}/player-stat")
        if not isinstance(payload, list):
            raise TypeError(f"Unexpected KBL player-stat response for {game_key}")
        return page, payload
