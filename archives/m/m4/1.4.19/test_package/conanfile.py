#!/usr/bin/env python3
"""Consumer test for GNU m4 as a packaged build tool."""

from pathlib import Path

from conan import ConanFile


class M4TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        self.run("sh test.sh", env="conanbuild")
        output = Path("output.txt").read_text(encoding="utf-8")
        expected = [
            "Hello, HarmonyOS",
            "42",
            "triplet-ok",
        ]
        for line in expected:
            if line not in output:
                raise AssertionError(f"m4 output missing {line!r}: {output!r}")
