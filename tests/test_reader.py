from datetime import datetime
from pathlib import Path

import httpx
import pytest

from fly.feeds.reader import (
    USER_AGENT,
    FetchError,
    FetchNetworkError,
    RobotsDisallowed,
    RobotsGate,
    fetch_text,
    parse_feed,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_parse_feed_items():
    items = parse_feed((FIXTURES / "feed_ppv.xml").read_text(), "pontospravoar")
    assert items[0].title.startswith("Alerta PPV! Viaje para Montevidéu")
    assert items[0].url == "https://pontospravoar.com/alerta-montevideu/"
    assert items[0].categories == ("Emissões com Pontos", "Smiles")
    assert items[0].published_at == datetime(2026, 10, 29, 9, 0)  # 12:00 UTC -> 09:00 in Sao Paulo
    assert items[0].feed == "pontospravoar" and len(items) == 2


def test_summary_strips_html():
    [item] = parse_feed((FIXTURES / "feed_pp.xml").read_text(), "passageirodeprimeira")
    assert "<" not in item.summary and "&amp;" not in item.summary
    assert item.summary == "Texto sintetico: ida & volta entre GRU e JNB."


def test_invalid_xml_raises():
    with pytest.raises(FetchError):
        parse_feed("<rss><channel>", "x")


def test_robots_disallow_blocks():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /feed/\n")
        return httpx.Response(200, text="<rss/>")

    client = _client(handler)
    with pytest.raises(RobotsDisallowed):
        fetch_text(client, RobotsGate(client), "https://x.test/feed/")


def test_robots_404_allows_and_sends_user_agent():
    seen = []

    def handler(request):
        seen.append(request.headers.get("user-agent"))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text="ok")

    client = _client(handler)
    assert fetch_text(client, RobotsGate(client), "https://x.test/feed/") == "ok"
    assert seen == [USER_AGENT, USER_AGENT]


def test_robots_fetched_once_per_host():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, text="User-agent: *\nAllow: /\n" if request.url.path == "/robots.txt" else "ok")

    client = _client(handler)
    gate = RobotsGate(client)
    fetch_text(client, gate, "https://x.test/a")
    fetch_text(client, gate, "https://x.test/b")
    assert calls.count("/robots.txt") == 1


def test_transport_error_is_network_error():
    def handler(request):
        raise httpx.ConnectError("offline")

    client = _client(handler)
    with pytest.raises(FetchNetworkError):
        fetch_text(client, RobotsGate(client), "https://x.test/feed/")


def test_http_500_is_fetch_error():
    def handler(request):
        return httpx.Response(404) if request.url.path == "/robots.txt" else httpx.Response(500)

    client = _client(handler)
    with pytest.raises(FetchError) as exc:
        fetch_text(client, RobotsGate(client), "https://x.test/feed/")
    assert not isinstance(exc.value, FetchNetworkError)
