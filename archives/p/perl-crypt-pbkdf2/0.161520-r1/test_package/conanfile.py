#!/usr/bin/env python3
"""Conan test_package — Crypt::PBKDF2 (pure Perl module).

Runs functional tests via test_pbkdf2.sh:
1. Verifies all expected .pm files are present
2. Syntax-checks each .pm file
3. If Perl runtime deps are available, runs PBKDF2 functional tests
   (generate, validate, RFC 6070 vectors, HMAC-SHA1/SHA2)
"""
import os

from conan import ConanFile


class PerlCryptPbkdf2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-crypt-pbkdf2"]
        perl_lib = os.path.join(dep.package_folder, "lib", "perl5")

        self.run(
            f'PERL5LIB="{perl_lib}" PERL_B_HOOKS_ENDOFSCOPE_BACKEND=PP bash test_pbkdf2.sh',
            cwd=self.source_folder,
        )
