#!/usr/bin/env python3
"""Conan test_package — ExtUtils::Builder::Compiler PurePerl module.

L1 test: Verify the Perl module exists in the package and loads correctly.
Also tests actual API functionality: creating a compiler object and
generating compile commands (R34: test must use actual API).

On OHOS with HMDFS, .pm loading may be affected by SELinux context.
The test script handles this internally.
"""
import os

from conan import ConanFile


class ExtUtilsBuilderCompilerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["extutils-builder-compiler"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib", "perl5")
        test_script = os.path.join(os.path.dirname(__file__), "test_module.sh")

        # R34: Run test script that loads the module and calls actual API
        # The script verifies .pm file presence, loads the module,
        # creates a compiler object, and generates compile commands.
        self.run(f'sh "{test_script}" "{perl_lib}"', env="conanrun")
        self.output.info("ExtUtils::Builder::Compiler test passed")
