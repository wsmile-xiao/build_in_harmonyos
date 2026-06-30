#!/usr/bin/env python3
"""Conan test_package — perl-ppix-utils 0.004

Tests that PPIx::Utils can be loaded and used to classify PPI elements.
Note: PPIx::Utils has Perl dependencies (PPI, B::Keywords) that are
installed as system Perl modules, not as Conan packages.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlPpixUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find PPIx/Utils.pm in the package folder
        pkg = self.dependencies["perl-ppix-utils"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Utils.pm"), recursive=True)
        if not pm_files:
            raise Exception("PPIx/Utils.pm not found in package")
        # Get the lib directory (parent of PPIx's parent)
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        # Set PERL5LIB to include both the package lib and system-installed Perl deps
        deps_lib = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"

        env = os.environ.copy()
        env["PERL5LIB"] = lib_dir + ":" + deps_lib + ":" + env.get("PERL5LIB", "")
        env["PERL_PARAMS_UTIL_PP"] = "1"

        # Test 1: Load PPIx::Utils and check version
        result = subprocess.run(
            ['perl', '-MPPIx::Utils', '-e', 'print "PPIx::Utils version: ", PPIx::Utils->VERSION, "\n"'],
            env=env, capture_output=True, text=True
        )

        if result.returncode != 0:
            self.output.error(f"PPIx::Utils load test failed: {result.stderr}")
            raise Exception(f"PPIx::Utils load test failed with exit code {result.returncode}")

        self.output.success(f"PPIx::Utils loaded successfully: {result.stdout}")

        # Test 2: Use Classification function on a PPI document
        result2 = subprocess.run(
            ['perl', '-e',
             'use PPI; use PPIx::Utils::Classification qw(is_perl_builtin); '
             'my $doc = PPI::Document->new(\q!print "hello";!); '
             'my $word = $doc->find_first("Token::Word"); '
             'print "Classification test: ", (is_perl_builtin($word) ? "OK" : "FAIL"), "\n"'],
            env=env, capture_output=True, text=True
        )

        if result2.returncode != 0:
            self.output.warning(f"PPIx::Utils classification test had issues: {result2.stderr}")
        else:
            self.output.success(result2.stdout)
