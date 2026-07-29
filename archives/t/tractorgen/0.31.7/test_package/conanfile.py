#!/usr/bin/env python3
"""Conan test_package — tractorgen 0.31.7

L1 smoke test: invoke test.sh which runs tractorgen 4 and verifies
stable ASCII tractor output fragments.
"""
import os
from conan import ConanFile

class TractorgenTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        pkg_folder = self.dependencies["tractorgen"].package_folder
        tg_bin = os.path.join(pkg_folder, "bin", "tractorgen")
        self.run(f"{bash} test.sh {tg_bin}", env="conanrun")
