#!/usr/bin/env python3
"""Consumer test for GNU make as a packaged build tool."""

from pathlib import Path

from conan import ConanFile


class MakeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        self.run("sh test.sh", env="conanbuild")
        version = Path("version.txt").read_text(encoding="utf-8")
        if "GNU Make 4.4.1" not in version:
            raise AssertionError(f"unexpected make version output: {version!r}")
        output = Path("output.txt").read_text(encoding="utf-8")
        recipe = Path("recipe-output.txt").read_text(encoding="utf-8")
        if "built-out.txt" not in output:
            raise AssertionError(f"make stdout missing rule echo: {output!r}")
        if "hello-from-gnu-make" not in recipe:
            raise AssertionError(f"recipe did not create target content: {recipe!r}")
