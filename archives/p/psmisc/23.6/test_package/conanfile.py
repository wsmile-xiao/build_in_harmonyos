#!/usr/bin/env python3
"""Conan test_package — psmisc 23.6.

Verifies that installed psmisc binaries execute correctly.
Runs pstree --version and killall --version as smoke tests.
"""
import os

from conan import ConanFile


class PsmiscTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # pstree --version exercises the ncurses-linked binary
        self.run("pstree --version", env="conanrun")
        # killall --version exercises the basic binary
        self.run("killall --version", env="conanrun")
