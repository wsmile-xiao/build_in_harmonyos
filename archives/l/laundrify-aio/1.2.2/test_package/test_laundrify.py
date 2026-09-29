#!/usr/bin/env python3
"""Smoke test for laundrify-aio 1.2.2 (run with staged site-packages on
sys.path — argv[1]). No upstream tests exist; this exercises the real
package surface: import, auth-code validation, API object construction,
and vendored pyjwt import.

Network calls to api.laundrify.de are intentionally NOT made (no server
access from CI); every assertion below is offline and deterministic.
"""
import sys

site = sys.argv[1]
sys.path.insert(0, site)

# 1. package imports (pulls in aiohttp + vendored jwt transitively)
import laundrify_aio  # noqa: E402
from laundrify_aio import LaundrifyAPI  # noqa: E402
from laundrify_aio.exceptions import (  # noqa: E402
    ApiConnectionException, InvalidFormat, UnauthorizedException,
    UnknownAuthCode)
import jwt  # noqa: E402  (vendored)

# 2. real API surface: offline helper from laundrify_aio.utils
from laundrify_aio.utils import validate_auth_code  # noqa: E402

assert validate_auth_code("123-456") is True, "valid auth code rejected"
assert validate_auth_code("12-3456") is False, "short code accepted"
assert validate_auth_code("abc-def") is False, "non-numeric code accepted"
assert validate_auth_code("") is False, "empty code accepted"

# 3. API object construction — pass a placeholder session to bypass
#    aiohttp ClientSession creation (needs a bound event loop whose
#    availability differs across conanrun env interpreters); the
#    constructor stores the session verbatim, so a dummy object
#    exercises the real constructor logic deterministically.
class _DummySession:
    pass

api = LaundrifyAPI(access_token="dummy-token", session=_DummySession())
assert api.access_token == "dummy-token"
assert api.host == "https://api.laundrify.de"
assert isinstance(api.client_session, _DummySession)
assert hasattr(api, "exchange_auth_code")
assert hasattr(LaundrifyAPI, "exchange_auth_code")

# 4. vendored pyjwt is functional (encode/decode round-trip)
token = jwt.encode({"sub": "laundrify-test"}, "secret", algorithm="HS256")
claims = jwt.decode(token, "secret", algorithms=["HS256"])
assert claims["sub"] == "laundrify-test", "pyjwt round-trip failed"

print("✅ laundrify-aio smoke test passed: imports + validate_auth_code "
      "+ LaundrifyAPI construction + pyjwt round-trip")
