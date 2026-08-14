#!/usr/bin/env python3
"""Conan test_package — perl-par-packer 1.064-r2.

Verifies that the PAR::Packer Perl module files are correctly packaged
and that the module can be loaded (with PAR_GLOBAL_TEMP workaround for
OHOS HMDFS restrictions).
"""
import os

from conan import ConanFile


class PerlParPackerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-par-packer"]
        test_script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f'sh "{test_script}" "{dep.package_folder}"', env="conanrun")
