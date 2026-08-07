#!/usr/bin/env python3
"""Consumer test for pyvolumio 0.1.5 — import API and exercise offline helpers.

Uses a mock aiohttp session so async Volumio methods can be verified without a
live Volumio device (R34: must exercise real packaged APIs).
"""
import asyncio
import sys


checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


class FakeResponse:
    def __init__(self, status=200, payload=None, raise_content_type=False):
        self.status = status
        self._payload = payload if payload is not None else {}
        self._raise_content_type = raise_content_type

    async def json(self):
        if self._raise_content_type:
            import aiohttp

            raise aiohttp.client_exceptions.ContentTypeError(
                request_info=None,
                history=(),
                message="not json",
            )
        return dict(self._payload)


class FakeSession:
    def __init__(self):
        self.calls = []
        self.closed = False
        self.next_response = FakeResponse(payload={"status": "play", "volume": 42})

    async def get(self, url, params=None):
        self.calls.append(("GET", url, params))
        return self.next_response

    async def post(self, url, json=None):
        self.calls.append(("POST", url, json))
        return self.next_response

    async def close(self):
        self.closed = True


def test_import_and_construct():
    from pyvolumio import CannotConnectError, Volumio

    check(Volumio is not None, "Volumio missing")
    check(issubclass(CannotConnectError, Exception), "CannotConnectError type")
    v = Volumio("10.0.0.5", 3000)
    check(v._host == "10.0.0.5", "host mismatch")
    check(v._port == 3000, "port mismatch")
    check(v._session is None, "default session should be None")
    check(callable(v.play), "play missing")
    check(callable(v.get_queue), "get_queue missing")
    print("PASS: pyvolumio public symbols / construct")


def test_canonic_url():
    from pyvolumio import Volumio

    v = Volumio("volumio.local", 3000)
    check(v.canonic_url(None) is None, "None url")
    check(
        v.canonic_url("https://cdn.example/a.jpg") == "https://cdn.example/a.jpg",
        "absolute https",
    )
    check(
        v.canonic_url("http://cdn.example/a.jpg") == "http://cdn.example/a.jpg",
        "absolute http",
    )
    check(
        v.canonic_url("/albumart?web=foo")
        == "http://volumio.local:3000/albumart?web=foo",
        "relative albumart",
    )
    check(
        v.canonic_url("albumart?web=bar")
        == "http://volumio.local:3000/albumart?web=bar",
        "relative without leading slash",
    )
    print("PASS: canonic_url helper")


def test_async_api_with_mock_session():
    from pyvolumio import CannotConnectError, Volumio

    async def run():
        session = FakeSession()
        v = Volumio("127.0.0.1", 3000, session=session)

        state = await v.get_state()
        check(state["status"] == "play", "get_state payload")
        check(state["volume"] == 42, "get_state volume")
        check(
            session.calls[-1][0:2]
            == ("GET", "http://127.0.0.1:3000/api/v1/getState"),
            "get_state URL",
        )

        session.next_response = FakeResponse(
            payload={"systemversion": "3.0", "builddate": "2021"}
        )
        info = await v.get_system_info()
        check(info["systemversion"] == "3.0", "get_system_info")

        session.next_response = FakeResponse(payload={"queue": [{"name": "a"}]})
        queue = await v.get_queue()
        check(queue == {"queue": [{"name": "a"}]}, "get_queue")

        session.next_response = FakeResponse(payload={})
        await v.play()
        check(
            session.calls[-1]
            == (
                "GET",
                "http://127.0.0.1:3000/api/v1/commands/",
                {"cmd": "play"},
            ),
            "play command",
        )

        await v.pause()
        check(session.calls[-1][2] == {"cmd": "pause"}, "pause command")

        await v.stop()
        check(session.calls[-1][2] == {"cmd": "stop"}, "stop command")

        await v.volume_up()
        check(
            session.calls[-1][2] == {"cmd": "volume", "volume": "plus"},
            "volume_up",
        )

        session.next_response = FakeResponse(
            payload={"navigation": {"lists": [{"title": "Music"}]}}
        )
        nav = await v.browse("music-library")
        check(nav == {"lists": [{"title": "Music"}]}, "browse navigation")
        check(
            session.calls[-1][2] == {"uri": "music-library"},
            "browse params",
        )

        session.next_response = FakeResponse(payload={"ok": True})
        await v.replace_and_play({"uri": "track:1"})
        check(
            session.calls[-1]
            == (
                "POST",
                "http://127.0.0.1:3000/api/v1/replaceAndPlay",
                {"uri": "track:1"},
            ),
            "replace_and_play",
        )

        # Non-JSON responses become empty dict (older Volumio compat)
        session.next_response = FakeResponse(raise_content_type=True)
        empty = await v.get_playlists()
        check(empty == {}, "content-type fallback")

        # HTTP error -> CannotConnectError
        session.next_response = FakeResponse(status=500, payload={})
        raised = False
        try:
            await v.get_state()
        except CannotConnectError:
            raised = True
        check(raised, "CannotConnectError on HTTP 500")

        # close() should not close caller-provided session
        await v.close()
        check(session.closed is False, "external session not closed")
        check(v._created_session is False, "created_session flag")

    asyncio.run(run())
    print("PASS: async API with mock session")


if __name__ == "__main__":
    tests = [
        test_import_and_construct,
        test_canonic_url,
        test_async_api_with_mock_session,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
        except Exception as e:
            print(f"FAIL: {fn.__name__}: {e}", file=sys.stderr)
            failed += 1
    if failed:
        print(f"\n{failed} test(s) FAILED (assertions so far: {checks})", file=sys.stderr)
        sys.exit(1)

    expected = 28
    if checks != expected:
        print(
            f"assertion count mismatch: expected {expected}, got {checks}",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"\nAll pyvolumio consumer tests passed ({checks}/{expected} assertions).")
    sys.exit(0)
