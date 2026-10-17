#!/usr/bin/env python3
"""Conan test_package — pinentry 1.3.2

L1 test: verify the pinentry-curses and pinentry-tty binaries run and report
their correct version number. This exercises the package's primary executables.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PinentryTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Compile the test program
        test_src = os.path.join(self.source_folder, "test_pinentry.c")
        test_bin = os.path.join(self.build_folder, "test_pinentry")
        self.run(f'clang "{test_src}" -o "{test_bin}"')

    def test(self):
        # R34: test must actually exercise the tested package's executables
        test_bin = os.path.join(self.build_folder, "test_pinentry")
        if can_run(self):
            self.run(f'"{test_bin}"', env="conanrun")
