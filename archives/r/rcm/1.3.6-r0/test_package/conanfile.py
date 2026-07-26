#!/usr/bin/env python3
"""Conan test_package for rcm 1.3.6-r0.

Verifies the rcm commands (lsrc, mkrc, rcup, rcdn) can manage dotfiles
via symlink creation and removal.
"""
import os
import shutil

from conan import ConanFile


class RcmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_rcm.sh")
        self.run(f'{bash} "{script}" "{pkg_folder}"',
                 env="conanrun")
