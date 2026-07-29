#!/usr/bin/env python3
"""Deterministic consumer checks for the packaged mdurl public API."""

import mdurl


checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


check(mdurl.__version__ == "0.1.2", "version mismatch")
check(mdurl.encode("my url") == "my%20url", "space encoding failed")
check(mdurl.encode("\r\n") == "%0D%0A", "control encoding failed")
check(mdurl.encode("%20") == "%20", "valid escape was not preserved")
check(mdurl.encode("%2G") == "%252G", "invalid escape was not encoded")
check(
    mdurl.encode("%20", keep_escaped=False) == "%2520",
    "keep_escaped=False failed",
)
check(
    mdurl.encode("\u03c6\u03bf\u03c5") == "%CF%86%CE%BF%CF%85",
    "Unicode encoding failed",
)
check(mdurl.decode("%F0%9F%91%A9") == "\U0001F469", "UTF-8 decoding failed")
check(mdurl.decode("%2F") == "%2F", "default decode exclusions failed")
check(
    mdurl.decode("%2F", exclude=mdurl.DECODE_COMPONENT_CHARS) == "/",
    "component decoding failed",
)

text = "https://user:pass@example.com:8443/a%20b?q=hello%20world#frag"
parsed = mdurl.parse(text)
check(isinstance(parsed, mdurl.URL), "parse did not return URL")
check(parsed.protocol == "https:", "protocol mismatch")
check(parsed.slashes is True, "slashes mismatch")
check(parsed.auth == "user:pass", "auth mismatch")
check(parsed.hostname == "example.com", "hostname mismatch")
check(parsed.port == "8443", "port mismatch")
check(parsed.pathname == "/a%20b", "pathname mismatch")
check(parsed.search == "?q=hello%20world", "search mismatch")
check(parsed.hash == "#frag", "fragment mismatch")
check(mdurl.format(parsed) == text, "format round trip failed")

print(f"PASS: mdurl packaged API consumer test ({checks}/20 assertions)")
