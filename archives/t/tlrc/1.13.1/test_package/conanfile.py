#!/usr/bin/env python3
"""Conan test_package for tlrc 1.13.1 — executable smoke test.

Verifies that the tldr binary is installed and functional:
- runs --version (expects tlrc v1.13.1)
- renders a local markdown page via --render
"""
import os

from conan import ConanFile


class TlrcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return

        # Get the tldr binary path from the dependency package
        tldr_bin = os.path.join(
            self.dependencies["tlrc"].package_folder, "bin", "tldr"
        )

        # Verify binary exists
        assert os.path.isfile(tldr_bin), f"tldr binary not found at {tldr_bin}"

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'TLDR_BIN="{tldr_bin}" {bash} test.sh', env="conanrun")
