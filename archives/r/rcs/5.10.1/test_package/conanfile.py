#!/usr/bin/env python3
"""Consumer test for GNU RCS as a packaged build tool."""

from pathlib import Path

from conan import ConanFile


class RcsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        self.run("sh test.sh", env="conanbuild")
        output = Path("output.txt").read_text(encoding="utf-8")
        expected = [
            "rcs-version-ok",
            "roundtrip-initial-ok",
            "roundtrip-second-ok",
            "checkout-rev1-ok",
            "rcsdiff-delta-ok",
            "rlog-two-revisions-ok",
            "ident-keyword-ok",
            "rcsclean-would-clean-ok",
            "rcsmerge-fold-ok",
        ]
        for line in expected:
            if line not in output:
                raise AssertionError(f"rcs test missing {line!r}: {output!r}")
