#!/usr/bin/env python3
"""Conan test_package for boops 1.0.0.

BOops is an LV2 glitch sequencer plugin — the test verifies the LV2
bundle (BOops.lv2) was installed correctly: bundle structure, TTL
metadata, ELF magic and lv2_descriptor symbol export.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class BoopsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["boops"]
        pkg_dir = dep.package_folder
        bundle_dir = os.path.join(pkg_dir, "lib", "lv2", "BOops.lv2")
        if not os.path.isdir(bundle_dir):
            raise ConanException(f"LV2 bundle not found: {bundle_dir}")
        # Resolve nm for symbol check
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        nm = compilers.get("nm") or shutil.which("llvm-nm") or shutil.which("nm") or "nm"
        script = os.path.join(self.recipe_folder, "test_boops.sh")
        if self.settings.os == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'{bash} "{script}" "{bundle_dir}" "{nm}"', env="conanrun")
        else:
            self.run(f'sh "{script}" "{bundle_dir}" "{nm}"', env="conanrun")
