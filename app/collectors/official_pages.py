"""Low-frequency collector that reads only KBL pages rendered in a browser."""
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from playwright.sync_api import sync_playwright

from app.config import Settings, get_settings

KBL_BASE_URL = "https://www.kbl.or.kr"
SEASON_LEADER_URL = f"{KBL_BASE_URL}/record/seasonLeader"


@dataclass(frozen=True)
class RenderedPage:
    url: str
    fetched_at: datetime
    title: str
    visible_text: str
    content_hash: str

    @property
    def body(self) -> str:
        return json.dumps({"title": self.title, "visible_text": self.visible_text}, ensure_ascii=False)


class KBLRenderedPageClient:
    """Reads visible text only; it never requests KBL's internal API endpoints."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def render(self, url: str) -> RenderedPage:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=self.settings.kbl_browser_channel, headless=True)
            page = browser.new_page(locale="ko-KR")
            page.goto(url, wait_until="domcontentloaded", timeout=int(self.settings.kbl_http_timeout_seconds * 1000))
            page.wait_for_timeout(1500)
            visible_text = page.locator("body").inner_text()
            title = page.title()
            final_url = page.url
            browser.close()
        return RenderedPage(
            url=final_url, fetched_at=datetime.now(UTC), title=title, visible_text=visible_text,
            content_hash=sha256(visible_text.encode("utf-8")).hexdigest(),
        )

    def render_season_leaders(self) -> RenderedPage:
        return self.render(SEASON_LEADER_URL)
