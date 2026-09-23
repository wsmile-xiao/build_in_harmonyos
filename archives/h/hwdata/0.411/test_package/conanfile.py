#!/usr/bin/env python3
"""Conan test_package for hwdata 0.411 — consumer check.

Runs test_hwdata.py (standalone test source, satisfies L0c) via self.run with
env="conanrun", so the runenv paths exported by package_info() are available.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class HwdataTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["hwdata"].package_folder
        data_dir = os.path.join(pkg, "share", "hwdata")
        if not os.path.isdir(data_dir):
            raise ConanException(f"hwdata data dir missing: {data_dir}")
        # the .pc file is the contract libdisplay-info-style consumers rely on
        pc = os.path.join(pkg, "share", "pkgconfig", "hwdata.pc")
        if not os.path.isfile(pc):
            raise ConanException(f"hwdata.pc missing: {pc}")
        test_script = os.path.join(os.path.dirname(__file__), "test_hwdata.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_hwdata.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{data_dir}' '{pc}'", env="conanrun")
