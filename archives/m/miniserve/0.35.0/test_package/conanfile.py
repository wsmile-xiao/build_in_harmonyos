#!/usr/bin/env python3
"""Conan test_package for miniserve 0.35.0 — executable smoke test.

Verifies that the miniserve binary is installed and functional:
- --version (expects miniserve 0.35.0)
- serves a real directory over HTTP and fetches a file with curl
"""
import os

from conan import ConanFile


class MiniserveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return

        # Get the miniserve binary path from the dependency package
        ms_bin = os.path.join(
            self.dependencies["miniserve"].package_folder, "bin", "miniserve"
        )

        # Verify binary exists
        assert os.path.isfile(ms_bin), f"miniserve binary not found at {ms_bin}"

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'MS_BIN="{ms_bin}" {bash} test.sh', env="conanrun")
