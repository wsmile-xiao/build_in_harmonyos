#!/usr/bin/env python3
"""Conan test_package — Crypt::Eksblowfish (Perl XS module).

Verifies that the packaged .so and .pm files are present in the correct
locations, then attempts to call the encryption API (R34). On OHOS, loading
the .so via DynaLoader may be blocked by SELinux policy (hmdfs context);
in that case the specific error is reported.
"""
import os

from conan import ConanFile


class PerlCryptEksblowfishTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-crypt-eksblowfish"]
        pkg_folder = dep.package_folder

        # Run the test script which checks .so/.pm existence, ELF validity,
        # and calls Blowfish encrypt/decrypt API (R34)
        test_script = os.path.join(os.path.dirname(__file__), "test_eksblowfish.sh")
        self.run(f"bash {test_script} {pkg_folder}")
