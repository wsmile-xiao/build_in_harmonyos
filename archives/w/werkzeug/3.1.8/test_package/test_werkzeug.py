#!/usr/bin/env python3
"""Consumer test for the installed werkzeug 3.1.8 package (R34).

Runs against the *packaged* tree only (site-packages passed on argv), so it
verifies what a downstream consumer actually gets: the importable package, the
sdist's dependency contract, and the .dist-info metadata that werkzeug's own
serving layer reads via importlib.metadata.version().

Every check is a real API call — no print-only assertion (R34).
"""
import os
import sys

SITE = sys.argv[1] if len(sys.argv) > 1 else None
if SITE:
    sys.path.insert(0, SITE)

failures = []
checks = 0


def check(label, cond, detail=""):
    global checks
    checks += 1
    if cond:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label} {detail}")
        failures.append(label)


# ---------------------------------------------------------------- version/dist-info
import importlib.metadata as md  # noqa: E402

import werkzeug  # noqa: E402
from werkzeug.exceptions import BadRequest  # noqa: E402
from werkzeug.http import (dump_cookie, http_date,  # noqa: E402
                           parse_accept_header)
from werkzeug.routing import Map, Rule  # noqa: E402
from werkzeug.test import Client  # noqa: E402
from werkzeug.wrappers import Request, Response  # noqa: E402

check("import werkzeug", werkzeug.__file__ is not None)
check("metadata.version == 3.1.8 (dist-info shipped)",
      md.version("werkzeug") == "3.1.8",
      f"got {md.version('werkzeug')!r}")

# ---------------------------------------------------------------- routing
m = Map([Rule("/user/<int:uid>", endpoint="user"),
         Rule("/static/<path:p>", endpoint="static")])
adapter = m.bind("example.test")
endpoint, args = adapter.match("/user/42")
check("routing match int converter", endpoint == "user" and args == {"uid": 42},
      f"got {endpoint!r} {args!r}")
endpoint, args = adapter.match("/static/css/app.css")
check("routing path converter", endpoint == "static"
      and args == {"p": "css/app.css"}, f"got {endpoint!r} {args!r}")
try:
    adapter.match("/nope")
    check("routing NotFound raised", False, "no exception")
except Exception as exc:
    check("routing NotFound raised",
          type(exc).__name__ == "NotFound", type(exc).__name__)

# ---------------------------------------------------------------- request/response
env = {
    "REQUEST_METHOD": "GET",
    "SERVER_NAME": "example.test",
    "SERVER_PORT": "80",
    "SERVER_PROTOCOL": "HTTP/1.1",
    "wsgi.url_scheme": "http",
    "PATH_INFO": "/hello",
    "QUERY_STRING": "a=1&a=2&b=x",
    "HTTP_HOST": "example.test",
}
req = Request(env)
check("Request.args multi-value", req.args.getlist("a") == ["1", "2"],
      f"got {req.args.getlist('a')!r}")
check("Request.args single", req.args.get("b") == "x")

resp = Response("hello <b>", status=201, mimetype="text/plain")
resp.headers["X-Custom"] = "yes"
check("Response status", resp.status_code == 201)
check("Response mimetype", resp.mimetype == "text/plain",
      f"got {resp.mimetype!r}")


@Request.application
def app(request):
    return Response(f"path={request.path}")


client = Client(app)
got = client.get("/hi")
check("Client GET body", got.get_data(as_text=True) == "path=/hi",
      f"got {got.get_data(as_text=True)!r}")
check("Client GET status", got.status_code == 200)

# ---------------------------------------------------------------- http helpers
check("http_date round-trip",
      http_date(0).startswith("Thu, 01 Jan 1970"), http_date(0))
# httponly defaults to False in 3.1.8, so it must be requested explicitly
cookie = dump_cookie("k", "v", max_age=60)
check("dump_cookie defaults (no HttpOnly/Secure)",
      "k=v" in cookie and "Max-Age=60" in cookie and "Path=/" in cookie
      and "HttpOnly" not in cookie and "Secure" not in cookie, cookie)
cookie_h = dump_cookie("k", "v", max_age=60, httponly=True, samesite="Lax")
check("dump_cookie httponly+samesite",
      "HttpOnly" in cookie_h and "SameSite=Lax" in cookie_h, cookie_h)
check("parse_accept_header quality",
      parse_accept_header("text/html;q=0.9,application/json").best
      == "application/json",
      str(parse_accept_header("text/html;q=0.9,application/json").best))

# ---------------------------------------------------------------- exceptions
br = BadRequest()
check("BadRequest code", br.code == 400, str(br.code))
check("BadRequest HTTPException subclass",
      br.get_response().status_code == 400)

# ---------------------------------------------------------------- security (negative)
from werkzeug.security import check_password_hash, generate_password_hash  # noqa: E402
h = generate_password_hash("secret", method="pbkdf2:sha256")
check("generate_password_hash format", h.startswith("pbkdf2:sha256:"), h[:20])
check("check_password_hash accepts", check_password_hash(h, "secret"))
check("check_password_hash rejects (negative)",
      not check_password_hash(h, "wrong"))

# ---------------------------------------------------------------- escaping via markupsafe
from werkzeug.utils import escape  # noqa: E402
check("escape escapes markup (negative)",
      escape("<script>") == "&lt;script&gt;", str(escape("<script>")))

# ---------------------------------------------------------------- platform-limited API
# Serving over AF_UNIX is refused by the platform (E024). Assert only that the
# API surface exists, so this stays a real check without pretending the
# platform allows the socket bind.
from werkzeug.serving import make_server  # noqa: E402
check("make_server importable", callable(make_server))

print(f"\n{checks - len(failures)}/{checks} checks passed")
if failures:
    print("FAILED: " + ", ".join(failures))
    sys.exit(1)
sys.exit(0)
