#!/usr/bin/env python3
"""Conan test_package — runit 2.3.1 (makefile)."""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.build import cross_building


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = Path(self.dependencies["runit"].cpp_info.bindirs[0])
        sv = bindir / "sv"
        runsv = bindir / "runsv"
        if not sv.is_file():
            raise RuntimeError(f"missing sv executable: {sv}")
        if not runsv.is_file():
            raise RuntimeError(f"missing runsv executable: {runsv}")
        if cross_building(self):
            self.output.info("cross-building: verified package executables exist")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_runit.sh '{sv}'", env="conanrun")
