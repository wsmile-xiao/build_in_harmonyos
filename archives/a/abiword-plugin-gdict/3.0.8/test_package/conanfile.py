#!/usr/bin/env python3
"""Conan smoke test for abiword-plugin-gdict."""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class AbiwordPluginGdictTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-compiling: defer gdict ABI smoke test to OHOS runner")
            return

        package_folder = self.dependencies["abiword-plugin-gdict"].package_folder
        shell = shutil.which("sh") or shutil.which("zsh") or "/system/bin/sh"
        script = os.path.join(self.source_folder, "test_gdict.sh")
        self.run(f'"{shell}" "{script}" "{package_folder}"', env="conanrun")
