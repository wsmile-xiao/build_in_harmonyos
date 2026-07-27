#!/usr/bin/env python3
"""Conan test_package for git-crypt 0.8.0.

R34: Test must actually depend on the tested package.
git-crypt is a CLI tool — the test runs the binary via test_git_crypt.sh.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class GitCryptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Actually execute the tested binary
        dep = self.dependencies["git-crypt"]
        git_crypt_bin = os.path.join(dep.package_folder, "bin", "git-crypt")
        test_script = os.path.join(self.source_folder, "test_git_crypt.sh")
        if can_run(self):
            self.run(
                f'bash "{test_script}" "{git_crypt_bin}"',
                env="conanrun",
            )
