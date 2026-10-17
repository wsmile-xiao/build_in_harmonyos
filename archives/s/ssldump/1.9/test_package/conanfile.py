#!/usr/bin/env python3
"""Conan test_package for ssldump 1.9 — verify ssldump binary executes."""
import os
from conan import ConanFile
from conan.tools.build import cross_building


class SsldumpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        bin_dir = self.dependencies["ssldump"].cpp_info.bindirs[0]
        pkg = self.dependencies["ssldump"].package_folder
        ssldump = os.path.join(pkg, bin_dir, "ssldump")
        if not os.path.exists(ssldump):
            raise Exception(f"ssldump binary not found at {ssldump}")
        out_file = os.path.join(self.build_folder, "ssldump_version.txt")
        self.run(f'"{ssldump}" -v > "{out_file}" 2>&1', env="conanrun")
        with open(out_file, "r", errors="ignore") as f:
            output = f.read()
        if "ssldump" not in output.lower() and "version" not in output.lower():
            raise Exception(f"ssldump version output not found, got: {output[:500]}")
        self.output.info("ssldump test PASSED")
