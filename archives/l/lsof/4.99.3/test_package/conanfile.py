#!/usr/bin/env python3
"""Conan test_package for lsof 4.99.3 (tool-type package).

Verifies the packaged lsof binary is installed and actually executes:
- `lsof -v` prints version/revision information
- `lsof -p <self pid>` lists the process' open files (real /proc scan)
"""
import os

from conan import ConanFile


class LsofTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return

        lsof_bin = os.path.join(
            self.dependencies["lsof"].package_folder, "bin", "lsof"
        )
        assert os.path.isfile(lsof_bin), f"lsof binary not found at {lsof_bin}"

        # OHOS: use bash to wrap binary execution (OHOS has no /bin/sh)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'LSOF_BIN="{lsof_bin}" {bash} test.sh', env="conanrun")
