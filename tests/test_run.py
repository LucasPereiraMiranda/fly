from datetime import datetime
from pathlib import Path

import httpx
import pytest

from fly.baseline import load_seeds
from fly.catalog import load_catalog
from fly.config import load_settings
from fly.run import build_feed_digest, run_feeds

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 29, 10, 0)
PPV_FEED = (FIXTURES / "feed_ppv.xml").read_text()
PP_FEED = (FIXTURES / "feed_pp.xml").read_text()
MVD_ARTICLE = """<div class="entry-content"><table>
<tr><th>Origem</th><th>Destino</th><th>Companhia Aérea</th><th>Trecho Clube/Diamante</th><th>Trecho Demais Clientes</th><th>Datas</th></tr>
<tr><td>Belo Horizonte (CNF)</td><td>Montevidéu (MVD)</td><td>GOL</td><td>27.000</td><td>28.000</td><td>15 de janeiro</td></tr>
</table></div>"""
LISBOA_FEED = """<?xml version="1.0"?><rss><channel><item>
<title>Viaje para Lisboa a partir de 50 mil milhas</title><link>https://pontospravoar.com/lisboa/</link>
<pubDate>Thu, 29 Oct 2026 12:00:00 +0000</pubDate><description>Texto sintetico</description>
</item></channel></rss>"""
LISBOA_ARTICLE = '<div class="entry-content"><p>Saidas de São Paulo (GRU) em 10 de fevereiro.</p></div>'


class Site:
    """Fake web: path -> response body / status / exception. Records requested paths."""

    def __init__(self, **overrides):
        self.routes = {
            "/robots.txt": 404,
            "passageirodeprimeira.com/feed/": PP_FEED,
            "pontospravoar.com/feed/": PPV_FEED,
            "pontospravoar.com/alerta-montevideu/": MVD_ARTICLE,
        }
        self.routes.update(overrides)
        self.requested = []

    def handler(self, request):
        key = request.url.host + request.url.path
        self.requested.append(key)
        answer = self.routes.get(request.url.path) if request.url.path == "/robots.txt" else self.routes.get(key, 404)
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, int):
            return httpx.Response(answer)
        return httpx.Response(200, text=answer)

    def client(self):
        return httpx.Client(transport=httpx.MockTransport(self.handler))


class FakeNotifier:
    def __init__(self, ok=True):
        self.ok, self.sent = ok, []

    def send(self, text):
        self.sent.append(text)
        return self.ok


@pytest.fixture
def settings(tmp_path):
    return load_settings(Path("config/fly.toml"), tmp_path / "none.env")


def _run(db, site, notifier, settings):
    return run_feeds(db=db, client=site.client(), notifier=notifier, catalog=load_catalog(),
                     seeds=load_seeds(), settings=settings, now=NOW)


def test_new_post_alerts_once(db, settings):
    site, notifier = Site(), FakeNotifier()
    report = _run(db, site, notifier, settings)
    assert report.alerts_sent == 1 and report.new_posts == 3
    assert "53% abaixo do normal" in notifier.sent[0] and "Menor já visto: 28.000 milhas" in notifier.sent[0]
    assert _run(db, site, notifier, settings).new_posts == 0
    assert len(notifier.sent) == 1


def test_card_post_never_fetches_article(db, settings):
    site = Site()
    _run(db, site, FakeNotifier(), settings)
    assert "pontospravoar.com/livelo-clube/" not in site.requested
    assert "passageirodeprimeira.com/joanesburgo/" not in site.requested


def test_one_feed_down_other_still_read(db, settings):
    site = Site(**{"pontospravoar.com/feed/": 500})
    report = _run(db, site, FakeNotifier(), settings)
    state = db.get_state("pontospravoar")
    assert report.failed_feeds == ["pontospravoar"]
    assert (state.failure_streak, state.last_error) == (1, "HTTP 500")
    assert "passageirodeprimeira.com/feed/" in site.requested


def test_network_error_does_not_pause(db, settings):
    _run(db, Site(**{"passageirodeprimeira.com/feed/": httpx.ConnectError("offline")}), FakeNotifier(), settings)
    state = db.get_state("passageirodeprimeira")
    assert state.status == "ok" and state.failure_streak == 1


def test_failed_send_retried_next_round(db, settings):
    site = Site()
    _run(db, site, FakeNotifier(ok=False), settings)
    notifier = FakeNotifier()
    report = _run(db, site, notifier, settings)
    assert report.alerts_sent == 1 and "53% abaixo" in notifier.sent[0]


def test_health_notice_after_three_failures(db, settings):
    site, notifier = Site(**{"pontospravoar.com/feed/": 500}), FakeNotifier()
    for _ in range(4):
        _run(db, site, notifier, settings)
    assert [t for t in notifier.sent if t.startswith("⚠️")] == [
        "⚠️ fly: fonte pontospravoar com problema (HTTP 500) — 3 falhas seguidas."
    ]


def test_digest_contains_unconfirmed_bh_post(db, settings):
    site = Site(**{"pontospravoar.com/feed/": LISBOA_FEED, "pontospravoar.com/lisboa/": LISBOA_ARTICLE})
    _run(db, site, FakeNotifier(), settings)
    text = build_feed_digest(db=db, settings=settings, now=NOW)
    assert "Viaje para Lisboa a partir de 50 mil milhas — confira se sai de BH — https://pontospravoar.com/lisboa/" in text


def _feed(*slugs):
    items = "".join(
        f"<item><title>Viaje para Lisboa a partir de 50 mil milhas {s}</title>"
        f"<link>https://pontospravoar.com/{s}/</link><pubDate>Thu, 29 Oct 2026 12:00:00 +0000</pubDate></item>"
        for s in slugs
    )
    return f"<rss><channel>{items}</channel></rss>"


def test_item_crash_does_not_stop_round(db, settings, monkeypatch):
    import fly.run

    real = fly.run.decide

    def flaky(item, article, *args, **kwargs):
        if "alerta-montevideu" in item.url and article is not None:
            raise ValueError("boom")
        return real(item, article, *args, **kwargs)

    monkeypatch.setattr(fly.run, "decide", flaky)
    report = _run(db, Site(), FakeNotifier(), settings)
    assert report.new_posts == 3
    assert db.post_seen("https://pontospravoar.com/alerta-montevideu/")
    assert "erro ao processar — confira" in build_feed_digest(db=db, settings=settings, now=NOW)


def test_article_layout_change_triggers_health_notice(db, settings):
    slugs = ("a", "b", "c")
    site = Site(**{"pontospravoar.com/feed/": _feed(*slugs)},
                **{f"pontospravoar.com/{s}/": "<html><body><p>novo layout</p></body></html>" for s in slugs})
    notifier = FakeNotifier()
    _run(db, site, notifier, settings)
    assert "⚠️ fly: fonte pontospravoar-artigo com problema (layout do artigo mudou) — 3 falhas seguidas." in notifier.sent


def test_run_guard_notifies_once_and_resets(db):
    from fly.run import run_guarded

    notifier = FakeNotifier()

    def boom():
        raise ValueError("seeds typo")

    for _ in range(2):
        run_guarded(boom, db=db, notifier=notifier)
    assert notifier.sent == ["⚠️ fly: execução falhou (ValueError). Veja data/logs/fly.log."]
    run_guarded(lambda: None, db=db, notifier=notifier)
    run_guarded(boom, db=db, notifier=notifier)
    assert len(notifier.sent) == 2
