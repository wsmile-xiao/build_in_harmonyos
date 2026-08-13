#!/usr/bin/env python3
"""Conan test_package for megatools homebrew.

Verifies the megatools binary is installed and runs correctly
via --version smoke test.
"""
import os
import shutil

from conan import ConanFile


class MegatoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_megatools.sh")
        self.run(f'{bash} {script} "{pkg_folder}"',
                 env="conanrun")
