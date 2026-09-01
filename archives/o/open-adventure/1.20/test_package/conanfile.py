#!/usr/bin/env python3
"""Conan test_package for open-adventure 1.20.

Runs test.sh which invokes the advent and cheat binaries to verify
they are executable in the conanrun environment.
"""
import os
import shutil

from conan import ConanFile


class OpenAdventureTestConan(ConanFile):
    """test_package for open-adventure — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R5: OHOS /system/bin/sh (mksh) cannot exec ELF binaries.
        # Three-layer fallback: CONFIG_SHELL → shutil.which → OHOS path
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f"{bash} {script}", env="conanrun")
