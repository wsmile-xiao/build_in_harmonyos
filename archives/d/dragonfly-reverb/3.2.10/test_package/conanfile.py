#!/usr/bin/env python3
"""Test package for dragonfly-reverb.

Validates LV2 plugin bundles: binary existence, manifest/metadata TTL
references, absence of UI references, and lv2_descriptor symbol export.
"""
import os
import shutil

from conan import ConanFile


class DragonflyReverbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        nm = (
            compilers.get("nm")
            or shutil.which("llvm-nm")
            or shutil.which("nm")
            or "nm"
        )

        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'bash "{test_script}" "{package_folder}" "{nm}"', env="conanrun")
