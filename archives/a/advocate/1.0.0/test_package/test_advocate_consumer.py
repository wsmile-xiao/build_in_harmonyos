"""Consumer test for advocate 1.0.0 — offline API checks (no network/DNS).

Exercises the real public API: version, IDNA canonicalization, IP
allow/deny decisions, blacklist/whitelist precedence, and the
RequestsAPIWrapper/Session wrapper behavior.
"""
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site:
    sys.path.insert(0, site)

import requests

import advocate
from advocate import AddrValidator
from advocate.addrvalidator import canonicalize_hostname
from advocate.api import RequestsAPIWrapper
from advocate.exceptions import MountDisabledException
from advocate.packages import ipaddress

TOTAL = 6
passed = 0

# 1. package version
assert advocate.__version__ == "1.0.0", advocate.__version__
passed += 1
print("[1/6] version ok")

# 2. IDNA hostname canonicalization (pure local, no DNS)
assert canonicalize_hostname("EDUCATIONAL.MUSEUM") == "educational.museum"
passed += 1
print("[2/6] canonicalize_hostname ok")

# 3. default validator blocks loopback (literal IP, no DNS)
validator = AddrValidator(autodetect_local_addresses=False)
assert validator.is_ip_allowed("127.0.0.1") is False
passed += 1
print("[3/6] loopback blocked ok")

# 4. default validator allows a public IP (literal IP, no DNS)
assert validator.is_ip_allowed("93.184.216.34") is True
passed += 1
print("[4/6] public IP allowed ok")

# 5. blacklist blocks, whitelist punches a hole (precedence)
guarded = AddrValidator(
    ip_blacklist={ipaddress.ip_network("10.0.0.0/8")},
    ip_whitelist={ipaddress.ip_network("10.1.0.0/16")},
    autodetect_local_addresses=False)
assert guarded.is_ip_allowed("10.2.0.1") is False
assert guarded.is_ip_allowed("10.1.0.1") is True
passed += 1
print("[5/6] blacklist/whitelist precedence ok")

# 6. wrapper API: Session subclass + mount() disabled
wrapper = RequestsAPIWrapper(
    validator=AddrValidator(autodetect_local_addresses=False))
session = wrapper.Session()
assert isinstance(session, requests.Session)
try:
    session.mount("foo://", None)
except MountDisabledException:
    pass
else:
    raise AssertionError("mount() did not raise MountDisabledException")
assert isinstance(advocate.Session(), requests.Session)
passed += 1
print("[6/6] wrapper API ok")

print("HMBS_TEST_PACKAGE_RESULT={\"executed\": true, \"passed\": true, "
      "\"command\": \"python test_advocate_consumer.py <site-packages>\", "
      "\"discovered\": %d, \"passedCount\": %d}" % (TOTAL, passed))
