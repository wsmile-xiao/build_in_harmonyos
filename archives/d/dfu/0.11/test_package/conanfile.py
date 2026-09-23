#!/usr/bin/env python3
"""Conan test_package for dfu-util 0.11.

Verifies installed CLI tools via test_dfu.sh: dfu-util/dfu-suffix/dfu-prefix
present + dfu-util --version + dfu-suffix file ops (no USB device needed).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class DfuUtilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["dfu"].package_folder
        bindir = os.path.join(pkg, "bin")
        script = os.path.join(self.source_folder, "test_dfu.sh")
        if cross_building(self):
            self.output.info("cross-building: only verifying test script exists")
            if not os.path.isfile(script):
                raise SystemExit("FAIL: test_dfu.sh missing")
            return
        self.run(f"sh {script} {bindir}", env="conanrun")
