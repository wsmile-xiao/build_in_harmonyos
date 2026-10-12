#!/usr/bin/env python3
"""test_package for puzzles (Simon Tatham's Portable Puzzle Collection) -
runs test_puzzles.sh, the 50-scenario suite, against the packaged binaries."""

import os

from conan import ConanFile


class PuzzlesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly.
        # Use bash to wrap binary execution (same pattern as ncmpcpp/rgbds).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_puzzles.sh", env="conanrun")
