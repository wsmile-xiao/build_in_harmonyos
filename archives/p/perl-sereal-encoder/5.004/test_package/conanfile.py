#!/usr/bin/env python3
"""Conan test_package for perl-sereal-encoder 5.004 (Perl XS module).

L1 test (R34): verify the Perl module files are present and call actual
Sereal::Encoder API (new + encode) to validate functionality.

Test script (test_encoder.py) performs:
  - Static checks: .pm existence/syntax, .so ELF/codesign/symbol/version
  - Runtime test: loads Sereal::Encoder and calls encode()
  - If "Permission denied" (HMDFS SELinux E046): tolerated, platform limitation
  - Any other load failure: test FAILS (real error, not silently swallowed)
"""
import os

from conan import ConanFile


class PerlSerealEncoderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["perl-sereal-encoder"]
        pkg = dep.package_folder
        arch = str(self.settings.arch)
        test_script = os.path.join(os.path.dirname(__file__), "test_encoder.py")
        self.run(f'python3 "{test_script}" "{pkg}" "{arch}"')
