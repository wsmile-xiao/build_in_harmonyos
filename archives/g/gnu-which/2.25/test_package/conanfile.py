#!/usr/bin/env python3
"""Conan test_package for gnu-which 2.25.

L1 test: verify the 'which' binary works correctly.
gnu-which is a CLI tool (not a library), so we test by running the binary
via a shell script (test_which.sh) that checks the version output.
"""
import os
import shutil

from conan import ConanFile


class GnuwhichTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R5: OHOS /system/bin/sh (mksh) cannot exec ELF binaries.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies["gnu-which"].package_folder
        which_bin = os.path.join(pkg_folder, "bin", "which")
        script = os.path.join(self.source_folder, "test_which.sh")
        self.run(f'{bash} {script} {which_bin}', env="conanrun")
