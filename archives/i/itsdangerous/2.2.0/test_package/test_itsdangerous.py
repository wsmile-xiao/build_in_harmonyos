#!/usr/bin/env python3
"""Consumer-side check for the packaged itsdangerous 2.2.0 (R34: real API).

Every assertion exercises the shipped package's public API — signing,
unsigning, tamper detection, expiry, serialisation round-trips and the
encoding helpers. No print-only stub, no import-only check.

``__version__`` is deliberately NOT asserted: itsdangerous resolves it lazily
through ``importlib.metadata.version("itsdangerous")`` (``__init__.py``
``__getattr__``), which requires a ``.dist-info`` directory on sys.path. This
packaging ships only the importable ``itsdangerous/`` directory, so that lookup
would raise PackageNotFoundError — a packaging artefact, not an API contract.
"""
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

import itsdangerous
from itsdangerous import (BadData, BadSignature, Serializer, SignatureExpired,
                          Signer, TimestampSigner, TimedSerializer,
                          URLSafeSerializer, URLSafeTimedSerializer,
                          base64_decode, base64_encode, want_bytes)

pkg_root = os.path.abspath(os.path.dirname(itsdangerous.__file__))
assert os.path.basename(pkg_root) == "itsdangerous", pkg_root

# --- Signer: sign / unsign round-trip ---------------------------------------
# NB: 2.x ``sign()`` returns **bytes** (use ``signer.sign(...).decode()`` for a
# str token, as Flask's docs do). Asserted explicitly so a future change of
# return type is caught rather than silently changing the contract.
signer = Signer("secret-key")
token = signer.sign("my-value")
assert isinstance(token, bytes), f"sign() returned {type(token).__name__}, expected bytes"
assert signer.unsign(token) == b"my-value"
assert token.count(b".") == 1, token

# --- tamper detection -------------------------------------------------------
try:
    signer.unsign(token + b"tampered")
    raise SystemExit("FAIL: BadSignature not raised for a tampered token")
except BadSignature:
    pass

# wrong key must also be rejected
try:
    Signer("other-key").unsign(token)
    raise SystemExit("FAIL: BadSignature not raised for a wrong key")
except BadSignature:
    pass

# --- TimestampSigner: expiry -------------------------------------------------
ts = TimestampSigner("secret-key")
ts_token = ts.sign("v")
assert ts.unsign(ts_token, max_age=3600) == b"v"
try:
    ts.unsign(ts_token, max_age=-1)
    raise SystemExit("FAIL: SignatureExpired not raised for max_age=-1")
except SignatureExpired:
    pass

# --- Serializers: round-trips ------------------------------------------------
ser = Serializer("secret-key")
assert ser.loads(ser.dumps({"a": 1})) == {"a": 1}
assert ser.loads(ser.dumps([1, 2, 3])) == [1, 2, 3]

url_ser = URLSafeSerializer("secret-key")
payload = {"user": "alice", "n": 42}
url_token = url_ser.dumps(payload)
assert url_ser.loads(url_token) == payload
# URLSafe output must contain no characters that need percent-encoding beyond
# the standard base64url alphabet plus itsdangerous' own '.' separator
assert set(url_token) <= set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.="
), url_token

timed_ser = TimedSerializer("secret-key")
t_token = timed_ser.dumps({"x": 1})
assert timed_ser.loads(t_token, max_age=3600) == {"x": 1}

url_timed = URLSafeTimedSerializer("secret-key")
ut_token = url_timed.dumps("hello")
assert url_timed.loads(ut_token, max_age=3600) == "hello"

# --- bad payload detection ---------------------------------------------------
try:
    ser.loads("not-a-valid-token")
    raise SystemExit("FAIL: BadData/BadSignature not raised for garbage input")
except (BadData, BadSignature):
    pass

# --- encoding helpers --------------------------------------------------------
# NB: both helpers speak **bytes** in 2.x — `base64_encode` returns bytes and
# `base64_decode` accepts str or bytes but always returns bytes (measured).
assert base64_encode(b"\x00\x01\x02") == b"AAEC", base64_encode(b"\x00\x01\x02")
assert isinstance(base64_encode(b"\x00\x01\x02"), bytes)
assert base64_decode("AAEC") == b"\x00\x01\x02", base64_decode("AAEC")
assert base64_decode(b"AAEC") == b"\x00\x01\x02", base64_decode(b"AAEC")
assert base64_encode(b"\x00\x01") == b"AAE", base64_encode(b"\x00\x01")  # padding stripped
assert want_bytes("abc") == b"abc"
assert isinstance(want_bytes("abc"), bytes)
assert want_bytes(b"abc") == b"abc"          # already bytes -> unchanged
assert want_bytes("héllo", encoding="utf-8") == "héllo".encode("utf-8")

print(f"itsdangerous consumer API: PASS ({pkg_root})")
