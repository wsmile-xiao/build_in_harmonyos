#!/usr/bin/env python3
"""Conan test_package for perl-sentinel.

Verifies that the Sentinel Perl module can be loaded and used.
Tests both get callback and value parameter functionality.
"""
import os

from conan import ConanFile


class PerlSentinelTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Test that the Sentinel module can be loaded and used
        test_script = (
            "use strict;\n"
            "use warnings;\n"
            "use Sentinel;\n"
            # Test 1: version
            "die 'version mismatch' unless Sentinel->VERSION eq '0.07';\n"
            # Test 2: get callback
            "my $x = sentinel(get => sub { 42 });\n"
            "die 'get callback failed' unless $x == 42;\n"
            # Test 3: value parameter
            "my $y = sentinel(value => 100);\n"
            "die 'value param failed' unless $y == 100;\n"
            # Test 4: get callback returning string
            "my $z = sentinel(get => sub { 'hello' });\n"
            "die 'string get failed' unless $z eq 'hello';\n"
            # Test 5: obj parameter
            "my $obj = bless { val => 99 }, 'TestObj';\n"
            "my $w = sentinel(obj => $obj, get => sub { $_[0]->{val} });\n"
            "die 'obj param failed' unless $w == 99;\n"
            "print 'Sentinel module loaded and working\\n';\n"
        )
        with open("test_sentinel.pl", "w") as f:
            f.write(test_script)
        self.run("perl test_sentinel.pl", env="conanrun")
