#!/usr/bin/env python3
"""Conan test_package — bzip2 1.0.8 smoke test.

Verifies package-provided binaries:
- bzip2 --version
- Actual compression/decompression via test.sh
"""
import os
import shutil

from conan import ConanFile


class Bzip2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify binary existence
        self.run("bzip2 --version", env="conanrun")
        # Run full compress/decompress smoke test
        script = os.path.join(self.source_folder, "test.sh")
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} {script}", env="conanrun")
