#!/usr/bin/env python3
"""Conan test_package for basez 1.6.2 — validates RFC 4648 encoding/decoding.

basez is a CLI tool (not a library), so the test runs the binary directly
with known test vectors from RFC 4648 Section 10 and verifies output.
"""
import os

from conan import ConanFile


class BasezTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the basez binary in the package's bindirs
        basez = os.path.join(
            self.dependencies["basez"].cpp_info.bindirs[0],
            "basez",
        )
        # Run smoke test with RFC 4648 test vectors.
        # Use bash if available, otherwise fall back to sh.
        bash = os.environ.get("CONFIG_SHELL", "")
        if not bash or not os.path.isfile(bash):
            bash = "/data/service/hnp/bin/bash"
        if not os.path.isfile(bash):
            bash = "sh"
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'{bash} "{test_script}" "{basez}"', env="conanrun")
