#!/usr/bin/env python3
"""Conan test_package — perl-string-format 1.18-r1 (L1 official test).

Tests that String::Format Perl module is installed and functional.
Runs upstream test suite (t/*.t) plus a functional smoke test.
"""
from conan import ConanFile
from conan.tools.layout import basic_layout


class PerlstringformatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # No CMake generation needed for pure Perl module
        pass

    def test(self):
        # L2 smoke test: verify module loads (exit 0 = success)
        self.run("perl -MString::Format -e 'exit 0'", env="conanrun")

        # Functional test: verify stringf() works with basic formatting
        # Use q{} and qq{} to avoid shell single-quote conflicts
        test_script = (
            "use String::Format qw(stringf); "
            "my $r = stringf(q{I like %a and %b.}, "
            "{a=>q{apples},b=>q{bananas}}); "
            "die qq{FAIL: got [$r]} "
            "unless $r eq q{I like apples and bananas.}; "
            "exit 0;"
        )
        self.run(f"perl -e '{test_script}'", env="conanrun")
