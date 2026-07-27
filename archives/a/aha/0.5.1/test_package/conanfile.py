#!/usr/bin/env python3
"""Conan test_package for aha (ANSI HTML Adapter).

Tests that the aha binary works correctly by:
1. Running `aha --version` to verify the binary executes
2. Converting a file with ANSI codes and checking for HTML output
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.layout import basic_layout


class AhaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        # Test 1: Verify aha binary executes
        self.run("aha --version", env="conanrun")

        # Test 2: Convert ANSI-coded file to HTML and verify output
        # R34: test must actually exercise the tested package's binary
        fd, tmp = tempfile.mkstemp(suffix='.txt')
        os.write(fd, b"\033[31mtest\033[0m")
        os.close(fd)
        try:
            self.run(f"aha -f {tmp} | grep -qi 'html'", env="conanrun")
        finally:
            os.unlink(tmp)
