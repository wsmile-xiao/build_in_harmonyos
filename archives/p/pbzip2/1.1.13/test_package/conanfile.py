#!/usr/bin/env python3
"""Conan test_package for pbzip2 1.1.13 — Conan L1 official test.

pbzip2 is a CLI tool, so the test runs the binary directly
instead of linking against a library. The test uses test_pbzip2.sh
which compresses and decompresses a file, then verifies content
integrity.
"""
import os
import stat

from conan import ConanFile


class Pbzip2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the pbzip2 binary in the package's bindirs
        pbzip2 = os.path.join(
            self.dependencies["pbzip2"].cpp_info.bindirs[0],
            "pbzip2"
        )
        # Ensure the test script is executable
        test_script = os.path.join(self.source_folder, "test_pbzip2.sh")
        if os.path.exists(test_script):
            st = os.stat(test_script)
            os.chmod(test_script, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        # Run the test script which compresses/decompresses and verifies integrity
        self.run(f'sh "{test_script}" "{pbzip2}"', env="conanrun")
