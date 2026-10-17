#!/usr/bin/env python3
"""Conan test_package for dgit 15.13.

Verifies that the Conan-packaged dgit scripts and Perl modules are
correctly installed.  Since dgit's main module Debian::Dgit depends
on Dpkg::Control::Hash (not available on OHOS), the test focuses on
file presence and loading modules that do NOT require Dpkg.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class DgitTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # L1: verify dgit script exists in the package
            self.run("test -f $(which dgit)", env="conanrun")

            # L2: verify Perl module Debian::Dgit::ExitStatus can be loaded
            #    (this module does NOT depend on Dpkg)
            test_script = os.path.join(os.path.dirname(__file__), "test.sh")
            self.run(f'sh "{test_script}"', env="conanrun")
