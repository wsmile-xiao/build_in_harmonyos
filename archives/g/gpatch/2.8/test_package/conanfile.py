#!/usr/bin/env python3
"""Conan test_package for gpatch 2.8.

L1 test: verify the 'patch' binary works correctly.
gpatch is a CLI tool (not a library), so we test by running the binary
via a shell script (test_patch.sh) that checks version output and basic patch functionality.
"""
import os
import shutil

from conan import ConanFile


class GpatchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies["gpatch"].package_folder
        patch_bin = os.path.join(pkg_folder, "bin", "patch")
        script = os.path.join(self.source_folder, "test_patch.sh")
        self.run(f'{bash} {script} {patch_bin}', env="conanrun")
