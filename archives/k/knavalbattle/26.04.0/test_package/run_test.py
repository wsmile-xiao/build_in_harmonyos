#!/usr/bin/env python3
"""Standalone smoke-test driver for the packaged knavalbattle binary.

This module is the independent test source file required by the CI L0c gate
(a test_package/ must contain a real source file besides conanfile.py).
test_package/conanfile.py::test() imports the check_run_output() helper here
and asserts the behaviour of the packaged `bin/knavalbattle --version`
execution.

The check mirrors the R34 contract: KAboutData::setupCommandLine +
QCommandLineParser::process print the version banner and exit 0 before any
display / DBus / network service is touched, so a valid run must

  * exit with status 0, and
  * print the application name and version on stdout/stderr.

The module is pure Python + stdlib only.
"""
import re

# Expected by KAboutData metadata: knavalbattle 2.1.26040 (26.04.0 release).
_VERSION_RE = re.compile(r"\bknavalbattle\b", re.I)
_NAME_RE = re.compile(r"\b2\.1\b|\b26\.04\b|2\.1\.26040")


def check_run_output(returncode: int, combined_output: str) -> None:
    """Assert a packaged-binary --version run is a genuine success."""
    if returncode != 0:
        raise AssertionError(
            f"packaged knavalbattle --version exited {returncode} "
            "(missing loader deps / broken ELF / unsigned binary?)"
        )
    if not _VERSION_RE.search(combined_output):
        raise AssertionError(
            "--version output does not mention 'knavalbattle': "
            f"{combined_output[:400]!r}"
        )
    if not _NAME_RE.search(combined_output):
        raise AssertionError(
            "--version output does not carry a version number: "
            f"{combined_output[:400]!r}"
        )
