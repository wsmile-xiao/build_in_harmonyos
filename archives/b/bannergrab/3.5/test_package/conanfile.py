#!/usr/bin/env python3
"""Conan test_package for bannergrab 3.5 — Conan L1 official test.

bannergrab is a CLI tool, so the test runs the binary directly
instead of linking against a library. The test uses test_bannergrab.py
which starts a TCP server with a known banner and verifies bannergrab
can grab it.
"""
import os

from conan import ConanFile


class BannergrabTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the bannergrab binary in the package's bindirs
        bannergrab = os.path.join(
            self.dependencies["bannergrab"].cpp_info.bindirs[0],
            "bannergrab"
        )
        # Run the test script which starts a TCP server and verifies banner grabbing
        test_script = os.path.join(self.source_folder, "test_bannergrab.py")
        self.run(f'python3 "{test_script}" "{bannergrab}"', env="conanrun")
