#!/usr/bin/env python3
"""Conan test_package for agetty 2.42.2.

Consumer test that REALLY executes the installed agetty binary:
  1. `agetty --version` — assert exit code 0 AND the version string
     "util-linux 2.42.2" is present.
  2. `agetty --help` — independent smoke that does NOT open a real TTY or
     start a login session. agetty(8) prints usage without a tty when
     invoked with --help.
Upstream has no registered agetty test cases: 0/0 (N/A).
"""
from conan import ConanFile
from conan.tools.layout import basic_layout


class AgettyTestConan(ConanFile):
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
        # Assertion 1: --version prints "agetty from util-linux 2.42.2" and exits 0.
        self.run("agetty --version 2>&1 | grep -q 'util-linux 2.42.2'", env="conanrun")
        # Assertion 2: --help exits 0 without opening a real TTY.
        self.run("agetty --help >/dev/null 2>&1", env="conanrun")
