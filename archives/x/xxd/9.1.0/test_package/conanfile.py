#!/usr/bin/env python3
"""Conan test_package for xxd 9.1.0.

Verifies that the xxd binary is installed and produces correct hex dumps.
xxd is a command-line tool, so we test by running it with known inputs
and comparing against expected output.
"""
import os
import shutil

from conan import ConanFile


class XxdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return

        # Get the xxd binary path from the dependency package
        xxd_bin = os.path.join(
            self.dependencies["xxd"].package_folder, "bin", "xxd"
        )

        # Verify binary exists
        assert os.path.isfile(xxd_bin), f"xxd binary not found at {xxd_bin}"

        # Find bash: prefer CONFIG_SHELL, then PATH lookup, then OHOS default
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(f'XXD_BIN="{xxd_bin}" {bash} test_xxd.sh', env="conanrun")
