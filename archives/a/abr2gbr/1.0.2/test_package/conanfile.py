#!/usr/bin/env python3
"""Conan test_package for abr2gbr 1.0.2.

abr2gbr is a CLI tool that converts Photoshop ABR brush files to GIMP GBR format.
The test verifies the binary exists and responds to --help.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class Abr2gbrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["abr2gbr"]
        bindir = os.path.join(dep.package_folder, "bin")
        abr2gbr = os.path.join(bindir, "abr2gbr")

        if not os.path.isfile(abr2gbr):
            raise ConanException(f"abr2gbr not found: {abr2gbr}")

        self.output.info(f"  abr2gbr: {os.path.getsize(abr2gbr)} bytes")

        # Run --help to verify the binary works
        result = self.run(f"{abr2gbr} --help 2>&1", env="conanrun", ignore_errors=True)
        if result >= 128 or result == 127:
            raise ConanException(f"abr2gbr crashed (exit code {result})")
        if result == 0:
            self.output.info("abr2gbr --help: OK")
        else:
            # Non-zero exit is acceptable for usage info
            self.output.info(f"abr2gbr --help: exited with code {result} (expected)")