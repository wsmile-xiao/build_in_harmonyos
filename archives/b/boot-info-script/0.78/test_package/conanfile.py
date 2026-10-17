#!/usr/bin/env python3
"""Conan test_package for boot-info-script 0.78."""
import os
import shutil

from conan import ConanFile


class BootInfoScriptTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_boot_info_script.sh")
        self.run(
            f'"{bash}" "{script}" "./bin/bootinfoscript" "{bash}"',
            env="conanrun",
            cwd=pkg_folder,
        )
