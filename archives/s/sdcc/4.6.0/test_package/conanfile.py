#!/usr/bin/env python3
"""Conan test_package for sdcc 4.6.0 — consumer check.

Runs test_sdcc.py (standalone test source, satisfies L0c) via self.run
with env="conanrun" (the conanrun PATH injection is required — a bare
subprocess would lose it, see yarl FileNotFoundError lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class SdccTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["sdcc"].package_folder
        bindir = os.path.join(pkg, "bin")
        if not os.path.isfile(os.path.join(bindir, "sdcc")):
            raise ConanException(f"sdcc binary missing under {bindir}")
        test_script = os.path.join(os.path.dirname(__file__), "test_sdcc.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_sdcc.py missing: {test_script}")
        # test_sdcc.py 期望 <package-folder>（内部拼 bin/sdcc + 复制整个
        # 包到非 HMDFS）——传 pkg 而非 bindir
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
