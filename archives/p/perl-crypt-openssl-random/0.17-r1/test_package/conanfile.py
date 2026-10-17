#!/usr/bin/env python3
"""Conan test_package — Crypt::OpenSSL::Random (Perl XS module).

Verifies that the packaged .so and .pm files are present in the correct
locations, the .so is a valid ELF shared object, and the module can be
loaded via Perl.

On OHOS, loading the .so via DynaLoader may be blocked by SELinux policy
(hmdfs:s0 context); in that case the test script verifies file existence,
ELF validity, and module loading is reported as a platform limitation.
"""
import os

from conan import ConanFile


class PerlcryptopensslrandomTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-crypt-openssl-random"]
        pkg_folder = dep.package_folder
        test_script = os.path.join(os.path.dirname(__file__), "test_package.py")
        self.run(f'python3 "{test_script}" "{pkg_folder}"')
