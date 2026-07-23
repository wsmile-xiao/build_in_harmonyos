#!/usr/bin/env python3
"""Conan test_package for mmv 2.10 (upstream v2.10).

Verifies the mmv binary can move/copy/link files with wildcard patterns.
Test adapted from Homebrew formula test suite.
"""
import os
import shutil

from conan import ConanFile


class MmvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_mmv.sh")
        self.run(f'{bash} {script} "{os.path.join(pkg_folder, "bin", "mmv")}"',
                 env="conanrun")
