#!/usr/bin/env python3
"""Conan test_package for coreutils-fmt 9.11.

Verifies that the fmt binary is installed and produces correct text wrapping.
fmt is a command-line tool, so we test by running it with known inputs
and comparing against expected output.
"""
import os

from conan import ConanFile


class CoreutilsFmtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return

        # Get the fmt binary path from the dependency package
        fmt_bin = os.path.join(
            self.dependencies["coreutils-fmt"].package_folder, "bin", "fmt"
        )

        # Verify binary exists
        assert os.path.isfile(fmt_bin), f"fmt binary not found at {fmt_bin}"

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'FMT_BIN="{fmt_bin}" {bash} test.sh', env="conanrun")
