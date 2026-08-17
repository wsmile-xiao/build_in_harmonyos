#!/usr/bin/env python3
"""Conan test_package for perl-parallel-prefork — Perl L1 test.

Tests that the installed Parallel::Prefork module files are correctly packaged.
Note: Full load test requires Proc::Wait3 (XS module) which cannot load
on OHOS due to ELF signing restrictions on .so files.
"""
import os

from conan import ConanFile


class PerlparallelpreforkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Manually set PERL5LIB to include the package's site_perl directory
        dep = self.dependencies["perl-parallel-prefork"]
        pkg_folder = dep.package_folder
        perl_site_lib = os.path.join(pkg_folder, "usr", "local", "lib", "site_perl", "5.42.0")
        from conan.tools.env import Environment
        env = Environment()
        env.append_path("PERL5LIB", perl_site_lib)
        env.vars(self).save_script("perl_env")

    def test(self):
        dep = self.dependencies["perl-parallel-prefork"]
        pkg_folder = dep.package_folder
        test_script = os.path.join(self.source_folder, "test_prefork.sh")
        self.run(f'sh "{test_script}" "{pkg_folder}"')
