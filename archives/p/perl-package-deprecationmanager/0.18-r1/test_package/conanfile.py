#!/usr/bin/env python3
"""Conan test_package for perl-package-deprecationmanager — L1 smoke test.

Verifies that Package::DeprecationManager can be loaded and used after installation.
Tests real API: import with -deprecations, deprecated(), custom message,
feature-based deprecation, warning capture.
"""
from conan import ConanFile


class PerlPackageDeprecationManagerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Smoke test: run test_deprecationmanager.sh which tests real API
        # The VirtualRunEnv generator sets PERL5LIB from the recipe's runenv_info
        test_script = "test_deprecationmanager.sh"
        self.run(f'sh "{test_script}"', env="conanrun")
