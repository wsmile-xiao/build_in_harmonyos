#!/usr/bin/env python3
"""Conan test_package — Perl smoke test for Role::Basic.

Verifies that the module can be loaded and role composition works correctly.
Uses subprocess to avoid shell quoting issues with complex Perl one-liners.
"""
import os
import subprocess

from conan import ConanFile


class PerlRoleBasicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a pure Perl smoke test

    def test(self):
        # Build PERL5LIB from the package's lib/perl5 directory
        perllib = []
        for dep in self.dependencies.values():
            perllib.append(os.path.join(dep.package_folder, "lib", "perl5"))
        perl5lib = ":".join(perllib)

        env = os.environ.copy()
        env["PERL5LIB"] = perl5lib

        # Test 1: Module loads and version is correct
        result = subprocess.run(
            ["perl", "-MRole::Basic", "-e", "print Role::Basic->VERSION"],
            env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise Exception(f"Failed to load Role::Basic: {result.stderr}")
        version = result.stdout.strip()
        self.output.info(f"Role::Basic version: {version}")

        # Test 2: Role composition — define a role, consume it, call method
        test_script = (
            "use strict; use warnings;"
            "package Role::Greetable; use Role::Basic;"
            "sub greet { return 'hello from role' };"
            "package My::Class; use Role::Basic 'with';"
            "with 'Role::Greetable';"
            "package main;"
            "my $o = bless {}, 'My::Class';"
            "die 'greet failed' unless $o->greet eq 'hello from role';"
            "print 'role composition OK'"
        )
        result = subprocess.run(
            ["perl", "-e", test_script],
            env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise Exception(f"Role composition test failed: {result.stderr}")
        self.output.info("Role composition (with) test PASSED")

        # Test 3: requires constraint works
        test_script_requires = (
            "use strict; use warnings;"
            "package Role::RequiresName; use Role::Basic;"
            "requires 'name';"
            "sub display { return 'Name: ' . shift->name };"
            "package My::NamedClass; use Role::Basic 'with';"
            "with 'Role::RequiresName';"
            "sub name { return 'HarmonyOS' };"
            "package main;"
            "my $o = bless {}, 'My::NamedClass';"
            "die 'requires test failed' unless $o->display eq 'Name: HarmonyOS';"
            "print 'requires constraint OK'"
        )
        result = subprocess.run(
            ["perl", "-e", test_script_requires],
            env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise Exception(f"requires constraint test failed: {result.stderr}")
        self.output.info("requires constraint test PASSED")

        self.output.info("Role::Basic smoke test PASSED")
