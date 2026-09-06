#!/usr/bin/env python3
"""Conan test_package — nsuds 0.7B.

nsuds is an interactive ncurses game, but it exposes fully non-interactive
--version/-v/--help/-h CLI paths that exit(0) before any ncurses init, so the
packaged binary can be exercised for real (R34 / PF3).  test.sh runs the
installed binary and asserts the actual output content.
"""
import os

from conan import ConanFile


class NsudsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the packaged binary and run the real smoke test (test.sh).
        pkg = self.dependencies["nsuds"].package_folder
        bin_path = os.path.join(pkg, "bin", "nsuds")
        self.output.info(f"nsuds binary under test: {bin_path}")
        self.run(f"bash test.sh {bin_path}", env="conanrun")
