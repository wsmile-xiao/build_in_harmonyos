#!/usr/bin/env python3
"""Conan test_package for perl-role-tiny — Perl smoke test.

Verifies that Role::Tiny can be loaded, used, and that core role functionality
works correctly on the target platform.

Tests:
  1. Module loads and version matches
  2. Basic role creation and application (with)
  3. requires constraint works
  4. DOES method correctly identifies roles
  5. Multiple role composition
  6. is_role detection
  7. apply_roles_to_object (runtime role application)
"""
import os

from conan import ConanFile


class PerlRoleTinyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a Perl module smoke test

    def test(self):
        # VirtualRunEnv sets PERL5LIB via conanrun environment
        # Test 1: Load module and check version
        self.run(
            'perl -MRole::Tiny -e '
            '\'print "Role::Tiny version: " . Role::Tiny->VERSION . "\\n";'
            'die "Version mismatch" unless Role::Tiny->VERSION eq "2.002004";\'',
            env="conanrun"
        )

        # Test 2-7: Functional smoke test covering core Role::Tiny features
        test_script = r'''
use strict;
use warnings;
use Role::Tiny;

# T2: Basic role creation and application
{ package R1; use Role::Tiny; sub greet { "hello" } }
{ package C1; use Role::Tiny::With; with "R1"; }
die "T2 FAIL" unless (bless({}, "C1"))->greet() eq "hello";

# T3: requires constraint
{ package R2; use Role::Tiny; requires "base"; sub enh { "e:" . shift->base() } }
{ package C2; use Role::Tiny::With; with "R2"; sub base { "b" } }
die "T3 FAIL" unless (bless({}, "C2"))->enh() eq "e:b";

# T4: DOES method
die "T4 FAIL" unless (bless({}, "C1"))->DOES("R1");
die "T4 FAIL" if (bless({}, "C1"))->DOES("NonExist");

# T5: Multiple roles
{ package RA; use Role::Tiny; sub ma { "a" } }
{ package RB; use Role::Tiny; sub mb { "b" } }
{ package MC; use Role::Tiny::With; with "RA", "RB"; }
die "T5 FAIL" unless (bless({}, "MC"))->ma() eq "a";
die "T5 FAIL" unless (bless({}, "MC"))->mb() eq "b";

# T6: is_role
die "T6 FAIL" unless Role::Tiny->is_role("R1");
die "T6 FAIL" if Role::Tiny->is_role("C1");

# T7: apply_roles_to_object
{ package SC; sub new { bless {}, shift } }
{ package LR; use Role::Tiny; sub lm { "late" } }
my $o = Role::Tiny->apply_roles_to_object(SC->new(), "LR");
die "T7 FAIL" unless $o->lm() eq "late";

print "All functional smoke tests PASSED\n";
'''
        # Write test script to a temp file and execute it
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pl', delete=False) as f:
            f.write(test_script)
            script_path = f.name
        try:
            self.run(f'perl {script_path}', env="conanrun")
        finally:
            os.unlink(script_path)

        self.output.info("Role::Tiny smoke test PASSED (version + 6 functional tests)")
