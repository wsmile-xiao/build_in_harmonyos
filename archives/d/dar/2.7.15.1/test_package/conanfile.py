#!/usr/bin/env python3
"""Conan test package for validating the dar executable package."""

import os
import shutil

from conan import ConanFile


class DarTestConan(ConanFile):
    """test_package for dar executable — verifies dar binary runs correctly."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        bindir = os.path.join(
            self.dependencies["dar"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_dar.sh")
        self.run(f'"{bash}" "{script}" "{bindir}"', env="conanrun")
