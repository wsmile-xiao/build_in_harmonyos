#!/usr/bin/env python3
"""Conan test_package for b2sum 20190724.

Verifies that the b2sum binary is installed and produces correct BLAKE2 hashes.
b2sum is a command-line tool, so we test by running it with known inputs
and comparing against official BLAKE2 reference vectors.
"""
import os

from conan import ConanFile


class B2sumTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return

        # Get the b2sum binary path from the dependency package
        b2sum_bin = os.path.join(
            self.dependencies["b2sum"].package_folder, "bin", "b2sum"
        )

        # Verify binary exists
        assert os.path.isfile(b2sum_bin), f"b2sum binary not found at {b2sum_bin}"

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution (R5: OHOS has no /bin/sh)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'B2SUM_BIN="{b2sum_bin}" {bash} test.sh', env="conanrun")
