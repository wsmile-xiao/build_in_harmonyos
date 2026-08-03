#!/usr/bin/env python3
"""Deterministic consumer checks for the packaged url-normalize API."""

import subprocess
import sys
from importlib.metadata import version

import idna
import url_normalize as package
from url_normalize import url_normalize


checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


check(package.__version__ == "2.2.1", "module version mismatch")
check(version("url-normalize") == "2.2.1", "distribution metadata missing")
check(idna.__version__ == "3.15", "bundled idna module version mismatch")
check(version("idna") == "3.15", "bundled idna metadata missing")
check(url_normalize(None) is None, "None handling failed")
check(url_normalize("") == "", "empty URL handling failed")
check(
    url_normalize("http://www.foo.com:80/foo") == "http://www.foo.com/foo",
    "default HTTP port removal failed",
)
check(
    url_normalize("http://example.com/a/../a/b") == "http://example.com/a/b",
    "dot-segment normalization failed",
)
check(
    url_normalize("http://www.foo.com/%7ebar") == "http://www.foo.com/~bar",
    "percent escape normalization failed",
)
check(
    url_normalize("пример.испытание/Служебная:Search/Test")
    == "https://xn--e1afmkfd.xn--80akhbyknj4f/"
    "%D0%A1%D0%BB%D1%83%D0%B6%D0%B5%D0%B1%D0%BD%D0%B0%D1%8F:Search/Test",
    "IDN or Unicode path normalization failed",
)
check(
    url_normalize("http://USER:pass@www.Example.COM/foo")
    == "http://USER:pass@www.example.com/foo",
    "userinfo or host normalization failed",
)
check(
    url_normalize("http://example.com/#!5753509/hello-world")
    == "http://example.com/?_escaped_fragment_=5753509/hello-world",
    "escaped-fragment normalization failed",
)
check(
    url_normalize("http://example.com/?q=C%CC%A7")
    == "http://example.com/?q=%C3%87",
    "Unicode NFC query normalization failed",
)
check(
    url_normalize(
        "https://www.google.com/search?q=test&utm_source=test",
        filter_params=True,
    )
    == "https://www.google.com/search?q=test",
    "default query filtering failed",
)
check(
    url_normalize(
        "https://google.com/search?qq=test&ie=utf8&utm_source=test",
        filter_params=True,
        param_allowlist=["ie", "qq"],
    )
    == "https://google.com/search?qq=test&ie=utf8",
    "list allowlist filtering failed",
)
check(
    url_normalize(
        "https://example.com/search?page=1&id=123&utm_source=test",
        filter_params=True,
        param_allowlist={"example.com": ["page", "id"]},
    )
    == "https://example.com/search?page=1&id=123",
    "domain allowlist filtering failed",
)
check(
    url_normalize("/foo.png", default_domain="example.com")
    == "https://example.com/foo.png",
    "default domain handling failed",
)
check(
    url_normalize("//www.foo.com/", default_scheme="http")
    == "http://www.foo.com/",
    "default scheme handling failed",
)
normalized = url_normalize("HTTP://EXAMPLE.COM:80/a/../b")
check(normalized == "http://example.com/b", "combined normalization failed")
check(url_normalize(normalized) == normalized, "normalization is not idempotent")

cli = subprocess.run(
    [sys.executable, "-m", "url_normalize.cli", "http://www.foo.com:80/foo"],
    check=False,
    capture_output=True,
    text=True,
)
check(cli.returncode == 0, f"module CLI failed: {cli.stderr}")
check(cli.stdout.strip() == "http://www.foo.com/foo", "CLI output mismatch")

cli_version = subprocess.run(
    [sys.executable, "-m", "url_normalize.cli", "--version"],
    check=False,
    capture_output=True,
    text=True,
)
check(cli_version.returncode == 0, f"CLI version failed: {cli_version.stderr}")
check(cli_version.stdout.strip().endswith("2.2.1"), "CLI version mismatch")

cli_filter = subprocess.run(
    [
        sys.executable,
        "-m",
        "url_normalize.cli",
        "-f",
        "https://www.google.com/search?q=test&utm_source=test",
    ],
    check=False,
    capture_output=True,
    text=True,
)
check(cli_filter.returncode == 0, f"CLI filter failed: {cli_filter.stderr}")
check(
    cli_filter.stdout.strip() == "https://www.google.com/search?q=test",
    "CLI filter output mismatch",
)

print(f"PASS: url-normalize packaged API consumer test ({checks}/26 assertions)")
