#!/usr/bin/env python3
"""Conan test_package for ait (GNU Emacs style editor).

Tests that the ait binary works correctly by:
1. Running `ait -v` to verify the binary executes and reports version
2. Checking the version string contains the expected version
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class AitTestConan(ConanFile):
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
        # R34: test must actually exercise the tested package's binary
        # Verify the version output contains the expected version string.
        self.run("ait -v | grep -q 'Ait 1.15'", env="conanrun")
