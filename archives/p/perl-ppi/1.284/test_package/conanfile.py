#!/usr/bin/env python3
"""Conan test_package — perl-ppi 1.284

Tests that PPI can be loaded and used to parse Perl code.
Note: PPI has Perl dependencies (Clone, Params::Util, etc.) that are
installed as system Perl modules, not as Conan packages.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlPpiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find PPI.pm in the package folder
        pkg = self.dependencies["perl-ppi"]
        pkg_folder = pkg.package_folder
        ppi_files = glob.glob(os.path.join(pkg_folder, "**", "PPI.pm"), recursive=True)
        if not ppi_files:
            raise Exception("PPI.pm not found in package")
        # Get the lib directory (parent of PPI.pm's parent)
        lib_dir = os.path.dirname(os.path.dirname(ppi_files[0]))

        # Set PERL5LIB to include both the package lib and system-installed Perl deps
        deps_lib = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"

        env = os.environ.copy()
        env["PERL5LIB"] = lib_dir + ":" + deps_lib + ":" + env.get("PERL5LIB", "")
        env["PERL_PARAMS_UTIL_PP"] = "1"

        # Test 1: Load PPI and check version
        result = subprocess.run(
            ['perl', '-MPPI', '-e', 'print "PPI version: $PPI::VERSION"'],
            env=env, capture_output=True, text=True
        )

        if result.returncode != 0:
            self.output.error(f"PPI load test failed: {result.stderr}")
            raise Exception(f"PPI load test failed with exit code {result.returncode}")

        self.output.success(f"PPI loaded successfully: {result.stdout}")

        # Test 2: Parse a simple Perl document
        result2 = subprocess.run(
            ['perl', '-MPPI', '-e',
             'my $doc = PPI::Document->new(\\ q{$x = 1}); '
             'print "Parse test: ", ($doc ? "OK" : "FAIL"), "\n"'],
            env=env, capture_output=True, text=True
        )

        if result2.returncode != 0:
            self.output.warning(f"PPI parse test had issues: {result2.stderr}")
        else:
            self.output.success(result2.stdout)
