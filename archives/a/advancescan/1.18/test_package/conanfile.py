#!/usr/bin/env python3
"""test_package for advancescan — executes advscan --version to verify the binary."""
import os
import shutil

from conan import ConanFile


class AdvancescanTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS has no /bin/bash; find bash dynamically with fallback to HNP path
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.run(f"{bash} test.sh", env="conanrun")
