from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from fly.sources.base import SourceNetworkError

BLOCKED_STATUSES = (403, 406)


class BrowserSession:
    """A real Chrome window with its own profile (never the user's personal profile).

    Sites behind Akamai only answer real browsers, so prices are read from the JSON
    responses the public search page itself requests.
    """

    def __init__(self, profile_dir: Path = Path.home() / ".fly/chrome-profile") -> None:
        self._profile_dir = profile_dir

    def __enter__(self) -> BrowserSession:
        self._profile_dir.mkdir(parents=True, exist_ok=True)
        self._pw = sync_playwright().start()
        self._context = self._pw.chromium.launch_persistent_context(
            str(self._profile_dir), channel="chrome", headless=False
        )
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        return self

    def __exit__(self, *exc) -> None:
        self._context.close()
        self._pw.stop()

    def fetch_json(self, url: str, match: str, timeout_ms: int = 30000) -> tuple[int, dict | None]:
        """Open `url` and return status + JSON of the first response whose URL contains `match`.

        A blocked page load returns its status with no JSON. No matching response within the
        timeout returns (0, None).
        """
        hits = []

        def on_response(response):
            if match in response.url:
                hits.append(response)

        self._page.on("response", on_response)
        try:
            nav = self._page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if nav is not None and nav.status in BLOCKED_STATUSES:
                return nav.status, None
            deadline = time.monotonic() + timeout_ms / 1000
            while not hits and time.monotonic() < deadline:
                self._page.wait_for_timeout(250)
            if not hits:
                return 0, None
            response = hits[0]
            try:
                return response.status, response.json()
            except (PlaywrightError, ValueError):
                return response.status, None
        except PlaywrightError as exc:
            if "net::" in str(exc):
                raise SourceNetworkError(str(exc).splitlines()[0]) from exc
            raise
        finally:
            self._page.remove_listener("response", on_response)
