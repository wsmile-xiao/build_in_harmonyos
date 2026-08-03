#!/usr/bin/env python3
"""Conan test_package — openocd 0.12.0.

L1 official test: verifies the openocd binary exists, prints its
version, and can be started in non-interactive mode.
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bin_path = os.path.join(
                self.dependencies[self.tested_reference_str].package_folder, "bin", "openocd"
            )
            if not os.path.isfile(bin_path):
                raise Exception(f"openocd binary not found: {bin_path}")
            ret = self.run(f"test -x \"{bin_path}\"")
            if ret != 0:
                raise Exception(f"openocd binary not executable: {bin_path}")
            ret = self.run(f"\"{bin_path}\" --version")
            if ret != 0:
                raise Exception(f"openocd --version failed with exit code {ret}")

            # L1 functional: verify version output via test.sh
            test_sh = os.path.join(self.source_folder, "test.sh")
            if os.path.isfile(test_sh):
                pkg_root = self.dependencies[self.tested_reference_str].package_folder
                ret = self.run(f"bash \"{test_sh}\" \"{pkg_root}\"")
                if ret != 0:
                    raise Exception(f"test.sh failed with exit code {ret}")
                self.output.info("L1 test PASS (openocd --version validated)")