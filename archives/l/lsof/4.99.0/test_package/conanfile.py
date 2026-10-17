#!/usr/bin/env python3
"""Conan test_package for lsof 4.99.0.

Verifies that the lsof binary is installed and can execute.
lsof is a command-line tool, so we test by running it with -v flag
to check version output.

Note: On OHOS, lsof may have limited functionality due to /proc
filesystem access restrictions. This test verifies the binary exists,
is a valid ELF, and can at least start execution.
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

        # Get the lsof binary path from the dependency package
        lsof_bin = os.path.join(
            self.dependencies["lsof"].package_folder, "bin", "lsof"
        )

        # Verify binary exists
        assert os.path.isfile(lsof_bin), f"lsof binary not found at {lsof_bin}"

        # OHOS: use bash to wrap binary execution (R5: OHOS has no /bin/sh)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'LSOF_BIN="{lsof_bin}" {bash} test.sh', env="conanrun")