from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import httpx

from fly.models import FeedItem

USER_AGENT = "fly-feed-reader/0.1 (uso pessoal)"
LOCAL_TZ = ZoneInfo("America/Sao_Paulo")


class FetchError(Exception):
    """The site answered, but not with something usable."""


class FetchNetworkError(FetchError):
    """Our own connectivity failed (offline, DNS, asleep)."""


class RobotsDisallowed(FetchError):
    """The site's robots.txt does not allow fly to read this URL."""


class RobotsGate:
    """Answers whether robots.txt allows a URL; reads each host's robots.txt once."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._parsers: dict[str, RobotFileParser | None] = {}

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._parsers:
            self._parsers[host] = self._load(host)
        parser = self._parsers[host]
        return parser is None or parser.can_fetch(USER_AGENT, url)

    def _load(self, host: str) -> RobotFileParser | None:
        try:
            resp = self._client.get(f"{host}/robots.txt", headers={"User-Agent": USER_AGENT})
        except httpx.TransportError as exc:
            raise FetchNetworkError(f"robots.txt: {type(exc).__name__}") from exc
        except httpx.HTTPError as exc:
            raise FetchError(f"robots.txt: {type(exc).__name__}") from exc
        if resp.status_code != 200:
            return None  # no robots.txt: everything is allowed
        parser = RobotFileParser()
        parser.parse(resp.text.splitlines())
        return parser


def fetch_text(client: httpx.Client, gate: RobotsGate, url: str) -> str:
    if not gate.allowed(url):
        raise RobotsDisallowed(url)
    try:
        resp = client.get(url, headers={"User-Agent": USER_AGENT})
    except httpx.TransportError as exc:
        raise FetchNetworkError(type(exc).__name__) from exc
    except httpx.HTTPError as exc:  # redirect loop, bad URL, undecodable body...
        raise FetchError(type(exc).__name__) from exc
    if resp.status_code != 200:
        raise FetchError(f"HTTP {resp.status_code}")
    return resp.text


def _plain(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_feed(xml: str, feed: str) -> list[FeedItem]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise FetchError("feed xml") from exc
    items = []
    for it in root.findall("./channel/item"):
        try:
            published = parsedate_to_datetime(it.findtext("pubDate"))
        except (TypeError, ValueError):
            continue  # an item without a usable date is skipped, not the whole feed
        items.append(FeedItem(
            feed=feed,
            url=(it.findtext("link") or "").strip(),
            title=_plain(it.findtext("title") or ""),
            summary=_plain(it.findtext("description") or ""),
            categories=tuple((c.text or "").strip() for c in it.findall("category")),
            published_at=published.astimezone(LOCAL_TZ).replace(tzinfo=None),
        ))
    if not items:
        raise FetchError("feed sem itens")  # a format change must not look like a quiet success
    return items
