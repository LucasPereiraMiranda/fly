from __future__ import annotations

import logging

import httpx

log = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, client: httpx.Client | None = None) -> None:
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._chat_id = chat_id
        self._client = client or httpx.Client(timeout=20)

    def send(self, text: str) -> bool:
        """Send a message; never raises. False means it was not delivered."""
        try:
            resp = self._client.post(
                self._url,
                json={"chat_id": self._chat_id, "text": text, "disable_web_page_preview": True},
            )
            ok = resp.status_code == 200 and resp.json().get("ok") is True
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("telegram send failed: %s", type(exc).__name__)
            return False
        if not ok:
            log.warning("telegram send rejected: HTTP %s", resp.status_code)
        return ok
