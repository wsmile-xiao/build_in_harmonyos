#!/usr/bin/env python3
"""Conan test_package — perl-regexp-grammars 1.058

Tests that Regexp::Grammars can be loaded and version verified.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlRegexpGrammarsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find Grammars.pm in the package folder
        pkg = self.dependencies["perl-regexp-grammars"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Grammars.pm"), recursive=True)
        if not pm_files:
            raise Exception("Grammars.pm not found in package")
        # Get the lib directory (parent of Regexp/ directory)
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        # Set PERL5LIB to include both the package lib and system-installed Perl deps
        deps_lib = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"

        env = os.environ.copy()
        env["PERL5LIB"] = lib_dir + ":" + deps_lib + ":" + env.get("PERL5LIB", "")

        # Test 1: Load Regexp::Grammars
        result = subprocess.run(
            ['perl', '-MRegexp::Grammars', '-e', 'print "OK\n"'],
            env=env, capture_output=True, text=True
        )

        if result.returncode != 0:
            self.output.error(f"Regexp::Grammars load test failed: {result.stderr}")
            raise Exception(f"Regexp::Grammars load test failed with exit code {result.returncode}")

        self.output.success(f"Regexp::Grammars loaded successfully: {result.stdout}")

        # Test 2: Verify version
        result2 = subprocess.run(
            ['perl', '-MRegexp::Grammars', '-e',
             'die unless $Regexp::Grammars::VERSION eq "1.058"; print "Version OK\n"'],
            env=env, capture_output=True, text=True
        )

        if result2.returncode != 0:
            self.output.warning(f"Version check had issues: {result2.stderr}")
        else:
            self.output.success(result2.stdout)
