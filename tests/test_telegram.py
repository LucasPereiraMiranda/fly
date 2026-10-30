import httpx

from fly.notify.telegram import TelegramNotifier


def _notifier(handler):
    return TelegramNotifier("TOKEN", "42", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_send_ok():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = request.read()
        return httpx.Response(200, json={"ok": True})

    assert _notifier(handler).send("oi") is True
    assert seen["url"] == "https://api.telegram.org/botTOKEN/sendMessage"
    assert b'"chat_id":"42"' in seen["body"].replace(b" ", b"")


def test_send_http_error_returns_false():
    assert _notifier(lambda r: httpx.Response(500, json={"ok": False})).send("oi") is False


def test_send_connection_error_returns_false():
    def handler(request):
        raise httpx.ConnectError("offline")

    assert _notifier(handler).send("oi") is False
