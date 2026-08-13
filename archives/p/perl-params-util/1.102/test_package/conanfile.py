#!/usr/bin/env python3
"""Conan test_package for perl-params-util — Perl L1 test.

Tests that the installed Params::Util module files exist in the package
and that core functions work correctly (pure Perl fallback mode).
Note: XS .so may fail to load due to SELinux/HMDFS restrictions,
but the pure Perl fallback (Params::Util::PP) works via PERL_PARAMS_UTIL_PP=1.
"""
import os

from conan import ConanFile


class PerlparamsutilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-params-util"]
        pkg_folder = pkg.package_folder

        # Run the test script which checks file existence and module functions
        script = os.path.join(self.source_folder, "test_params_util.sh")
        self.run(f'bash "{script}" "{pkg_folder}"', env="conanrun")
