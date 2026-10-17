#!/usr/bin/env python3
"""Conan test_package — perl-xml-parser 2.59

Verifies the package was built correctly by attempting to load
the XML::Parser module and call its API. If SELinux blocks module
loading on OHOS, falls back to readelf verification of the
boot_XML__Parser__Expat XS entry point symbol (R34 compliant).
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class PerlXmlParserTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies["perl-xml-parser"]
        lib_dir = os.path.join(dep.package_folder, "lib")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{lib_dir}"', env="conanrun")
