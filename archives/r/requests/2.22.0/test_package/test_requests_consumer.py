#!/usr/bin/env python3
"""Consumer-side check for the packaged requests 2.22.0 (R34: real API).

Drives the shipped library through its public surface: PreparedRequest
construction/URL parsing, Session + adapter wiring, streaming bodies, auth
hooks, exceptions hierarchy and the dependency-warning behaviour that this
adaptation deliberately accepts (newer, already-published deps).

Network calls are limited to one real HTTPS GET; everything else is offline so
the check stays deterministic on a build machine without internet access.
"""
import os
import sys
import warnings

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

# The newer published deps do not satisfy requests 2.22.0's own
# check_compatibility() asserts -> one advisory RequestsDependencyWarning.
# Capture it instead of letting it pollute stderr, and assert it IS the
# expected (and only) one, so an unexpected warning regression is caught.
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    import requests
    from requests.exceptions import RequestsDependencyWarning

assert requests.__version__ == "2.22.0", requests.__version__
dep_warnings = [w for w in caught
                if issubclass(w.category, RequestsDependencyWarning)]
assert len(dep_warnings) == 1, [str(w.message) for w in caught]
assert "doesn't match a supported version" in str(dep_warnings[0].message)

pkg_root = os.path.abspath(os.path.dirname(requests.__file__))
assert os.path.basename(pkg_root) == "requests", pkg_root

# --- PreparedRequest / URL parsing ------------------------------------------
from requests import Request, Session
from requests.models import PreparedRequest

p = Request("GET", "https://example.invalid/path?a=1&b=2",
            params={"c": "3"}).prepare()
assert p.method == "GET"
assert "a=1" in p.url and "c=3" in p.url
# body-less GET: requests only sets Content-Length when there is a body
assert p.headers.get("Content-Length") in (None, "0")

# non-ASCII host goes through idna
p2 = Request("GET", "https://例え.テスト/").prepare()
assert p2.url.startswith("https://xn--r8jz45g.xn--zckzah/"), p2.url

# --- Session + adapter wiring ----------------------------------------------
s = Session()
assert type(s.get_adapter("https://x")).__name__ == "HTTPAdapter"
assert type(s.get_adapter("http://x")).__name__ == "HTTPAdapter"
s.headers.update({"X-Test": "harmony"})
assert s.headers["X-Test"] == "harmony"

# --- streaming body + prepared copy ----------------------------------------
from io import BytesIO
req = PreparedRequest()
req.prepare(method="POST", url="https://example.invalid/upload",
            data=BytesIO(b"harmonyos"))
assert req.body.read() == b"harmonyos"
cp = req.copy()
assert cp.method == "POST" and cp.url == req.url

# --- retry config accepts a urllib3 Retry object ----------------------------
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
s.mount("https://", HTTPAdapter(max_retries=Retry(total=1)))
assert isinstance(s.get_adapter("https://x"), HTTPAdapter)

# --- exceptions hierarchy ---------------------------------------------------
import requests.exceptions as rexc
assert issubclass(rexc.ConnectTimeout, rexc.ConnectionError)
assert issubclass(rexc.ReadTimeout, rexc.Timeout)
for name in ("ConnectionError", "ReadTimeout", "SSLError", "ProxyError",
             "RetryError", "Timeout"):
    assert hasattr(rexc, name), name

# --- one real HTTPS GET -----------------------------------------------------
# Only connectivity failures are tolerated (build machines may be offline).
# Explicitly NOT swallowed: a reachable-network regression (non-200, empty
# body, missing encoding) must fail the test — a bare `except Exception`
# around the assertions would turn it into a green "skipped".
online = False
try:
    r = requests.get("https://pypi.org/simple/docopt/", timeout=30)
except (requests.exceptions.ConnectionError,
        requests.exceptions.Timeout) as e:
    print(f"  (network GET skipped, offline build machine: "
          f"{type(e).__name__})")
else:
    online = True
    assert r.status_code == 200, r.status_code
    assert len(r.content) > 0
    assert r.encoding is not None

print(f"requests {requests.__version__} consumer API: PASS "
      f"({pkg_root}, network={'yes' if online else 'no'})")
