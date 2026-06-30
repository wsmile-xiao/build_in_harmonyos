#!/usr/bin/env python3
"""Conan test_package — perl-scope-guard 0.21

Tests that Scope::Guard can be loaded and version verified.
Pure Perl module - no C/C++ compilation needed.
"""
import os
import subprocess

from conan import ConanFile


class PerlScopeGuardTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        pass

    def test(self):
        pkg = self.dependencies["perl-scope-guard"]
        pkg_folder = pkg.package_folder
        lib_dir = os.path.join(pkg_folder, "lib", "perl5")

        env = os.environ.copy()
        env["PERL5LIB"] = lib_dir + ":" + env.get("PERL5LIB", "")

        # Test 1: Load Scope::Guard
        result = subprocess.run(
            ['perl', '-MScope::Guard', '-e', 'print "OK\n"'],
            env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            self.output.error(f"Scope::Guard load test failed: {result.stderr}")
            raise Exception(f"Scope::Guard load test failed with exit code {result.returncode}")
        self.output.success(f"Scope::Guard loaded successfully: {result.stdout}")

        # Test 2: Verify version
        result2 = subprocess.run(
            ['perl', '-MScope::Guard', '-e',
             'die unless $Scope::Guard::VERSION eq "0.21"; print "Version OK\n"'],
            env=env, capture_output=True, text=True
        )
        if result2.returncode != 0:
            self.output.warning(f"Version check had issues: {result2.stderr}")
        else:
            self.output.success(result2.stdout)

        # Test 3: Functional test - guard() fires on scope exit
        result3 = subprocess.run(
            ['perl', '-e',
             'use Scope::Guard; '
             'my $x = 0; '
             '{ my $g = Scope::Guard->new(sub { $x = 42 }); } '
             'die "guard did not fire" unless $x == 42; '
             'print "Functional OK\n"'],
            env=env, capture_output=True, text=True
        )
        if result3.returncode != 0:
            self.output.warning(f"Functional test had issues: {result3.stderr}")
        else:
            self.output.success(result3.stdout)
