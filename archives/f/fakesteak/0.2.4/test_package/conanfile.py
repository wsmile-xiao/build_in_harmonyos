#!/usr/bin/env python3
"""Conan test_package for fakesteak 0.2.4 — Conan L1 official test.

fakesteak is a CLI tool, so the test runs the binary directly
instead of linking against a library. The test verifies that
the binary runs and prints correct version/help output.
"""
import os

from conan import ConanFile


class FakesteakTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must substantively depend on the tested package
        # Find the fakesteak binary in the package's bindirs
        fakesteak = os.path.join(
            self.dependencies["fakesteak"].cpp_info.bindirs[0],
            "fakesteak"
        )
        # Run the test script which verifies version and help output
        test_script = os.path.join(self.source_folder, "test_fakesteak.sh")
        self.run(f'bash "{test_script}" "{fakesteak}"', env="conanrun")
