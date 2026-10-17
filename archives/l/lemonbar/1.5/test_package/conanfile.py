#!/usr/bin/env python3
"""test_package for lemonbar — really executes the installed binary (R34).

test_lemonbar.sh runs the packaged `lemonbar` with no reachable X display and
asserts on its documented startup behaviour and exit status; it fails if the
binary is missing, not executable, or cannot resolve its bundled shared
libraries (CI L1e sabotages bin/ to prove this dependency).
"""
import os

from conan import ConanFile


class LemonbarTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run("{0} test_lemonbar.sh".format(shell), env="conanrun")
