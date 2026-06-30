#!/usr/bin/env python3
"""Conan test_package — perl-regexp-tr 0.05 (Regexp::Tr)

Perl smoke test: load the module and exercise basic tr/// functionality.
"""
import os

from conan import ConanFile
from conan.tools.files import save


class PerlRegexpTrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        pass

    def test(self):
        # Write a small Perl test script to avoid shell escaping issues
        # Uses the correct Regexp::Tr API: bind() and trans() methods
        test_script = (
            "use Regexp::Tr;\n"
            "my $tr = Regexp::Tr->new('a-z','A-Z');\n"
            "die 'new failed' unless defined $tr;\n"
            "my $s = 'hello';\n"
            "$tr->bind(\\$s);\n"
            "die 'bind failed' unless $s eq 'HELLO';\n"
            "my $r = $tr->trans('world');\n"
            "die 'trans failed' unless $r eq 'WORLD';\n"
            "print \"Regexp::Tr smoke test OK\\n\";\n"
        )
        save(self, "test_regexp_tr.pl", test_script)
        self.run("perl test_regexp_tr.pl", env="conanrun")
