#!/usr/bin/env python3
"""Conan test_package for rbenv-bundler 1.0.1

Verifies that the rbenv-bundler plugin scripts are correctly installed
and the main binary is executable with proper shell syntax.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class RbenvBundlerTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        pkg_folder = self.dependencies["rbenv-bundler"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "rbenv-bundler")
        includes_path = os.path.join(pkg_folder, "etc", "rbenv.d", "bundler", "includes.sh")

        # Run the test script
        test_script = os.path.join(self.source_folder, "test_rbenv_bundler.sh")
        self.run(f'bash "{test_script}" "{bin_path}" "{includes_path}"', env="conanrun")

        # Also verify --complete output directly (RBENV_ROOT needed for md5 call)
        self.run(f'RBENV_ROOT=/tmp/test-rbenv "{bin_path}" --complete', env="conanrun")
