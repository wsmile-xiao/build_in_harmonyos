#!/usr/bin/env python3
"""Conan test_package — perl-math-pari 2.030528-r1

Verifies the package was built correctly by attempting to load
the Math::Pari module and call its API. If SELinux blocks module
loading on OHOS (manifest G2 known failure), falls back to readelf
verification of the boot_Math__Pari XS entry point symbol (R34 compliant).
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class PerlMathPariTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies["perl-math-pari"]
        lib_dir = os.path.join(dep.package_folder, "lib")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{lib_dir}"', env="conanrun")
