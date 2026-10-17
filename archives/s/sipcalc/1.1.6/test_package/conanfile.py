#!/usr/bin/env python3
"""Conan test_package for sipcalc 1.1.6 — CLI smoke test.

L1 test: verify the sipcalc binary is installed and produces correct output.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class SipcalcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Find the sipcalc binary in the package folder
            dep = self.dependencies["sipcalc"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            sipcalc_cmd = os.path.join(bin_dir, "sipcalc")

            # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
            # Use bash to wrap binary execution.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

            # Run test.sh smoke test (source file for CI L0c compliance)
            self.run(f'{bash} test.sh "{sipcalc_cmd}"', env="conanrun")