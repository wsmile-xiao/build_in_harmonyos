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

        # Verify that the Perl module files are installed in the package
        prefork_pm = os.path.join(pkg_folder, "usr", "local", "lib", "site_perl", "5.42.0", "Parallel", "Prefork.pm")
        spareworkers_pm = os.path.join(pkg_folder, "usr", "local", "lib", "site_perl", "5.42.0", "Parallel", "Prefork", "SpareWorkers.pm")
        scoreboard_pm = os.path.join(pkg_folder, "usr", "local", "lib", "site_perl", "5.42.0", "Parallel", "Prefork", "SpareWorkers", "Scoreboard.pm")

        assert os.path.isfile(prefork_pm), f"Parallel/Prefork.pm not found in package: {prefork_pm}"
        assert os.path.isfile(spareworkers_pm), f"Parallel/Prefork/SpareWorkers.pm not found in package: {spareworkers_pm}"
        assert os.path.isfile(scoreboard_pm), f"Parallel/Prefork/SpareWorkers/Scoreboard.pm not found in package: {scoreboard_pm}"

        # Verify the module version matches
        self.run(f"perl -e 'open(F,\"{prefork_pm}\"); $c=join(\"\",<F>); "
                 f"die \"version mismatch\" unless $c =~ /\\$VERSION\\s*=\\s*[\\x27\\\"]0\\.18[\\x27\\\"]/; "
                 f"print \"Parallel::Prefork v0.18 verified OK\\n\";'")
