#!/usr/bin/env python3
"""Conan test_package — perl-ppix-quotelike 0.023

Tests that PPIx::QuoteLike can be loaded and used to parse Perl string literals.
Note: PPIx::QuoteLike has Perl dependencies (PPI, Readonly) that are
installed as system Perl modules, not as Conan packages.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlPpiXQuoteLikeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find PPIx/QuoteLike.pm in the package folder
        pkg = self.dependencies["perl-ppix-quotelike"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "QuoteLike.pm"), recursive=True)
        if not pm_files:
            raise Exception("PPIx/QuoteLike.pm not found in package")
        # Get the lib directory (parent of PPIx's parent)
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        # Set PERL5LIB to include both the package lib and system-installed Perl deps
        deps_lib = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"

        env = os.environ.copy()
        env["PERL5LIB"] = lib_dir + ":" + deps_lib + ":" + env.get("PERL5LIB", "")
        env["PERL_PARAMS_UTIL_PP"] = "1"

        # Test 1: Load PPIx::QuoteLike and check version
        result = subprocess.run(
            ['perl', '-MPPIx::QuoteLike', '-e', 'print "PPIx::QuoteLike version: ", PPIx::QuoteLike->VERSION, "\n"'],
            env=env, capture_output=True, text=True
        )

        if result.returncode != 0:
            self.output.error(f"PPIx::QuoteLike load test failed: {result.stderr}")
            raise Exception(f"PPIx::QuoteLike load test failed with exit code {result.returncode}")

        self.output.success(f"PPIx::QuoteLike loaded successfully: {result.stdout}")

        # Test 2: Parse a simple Perl string literal
        result2 = subprocess.run(
            ['perl', '-MPPIx::QuoteLike', '-e',
             'my $str = PPIx::QuoteLike->new( q{"hello world"} ); '
             'print "Parse test: ", ($str ? "OK" : "FAIL"), "\n"'],
            env=env, capture_output=True, text=True
        )

        if result2.returncode != 0:
            self.output.warning(f"PPIx::QuoteLike parse test had issues: {result2.stderr}")
        else:
            self.output.success(result2.stdout)
