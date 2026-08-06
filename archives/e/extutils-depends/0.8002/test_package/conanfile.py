#!/usr/bin/env python3
"""Conan test_package for extutils-depends — Perl L1 test.

Verifies that the installed ExtUtils::Depends module can be loaded and used.
"""
import glob
import os
import tempfile

from conan import ConanFile


class ExtUtilsDependsTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the installed module path from the dependency
        dep = self.dependencies["extutils-depends"]
        pkg_folder = dep.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "ExtUtils", "Depends.pm"), recursive=True)
        if not pm_files:
            raise Exception("ExtUtils/Depends.pm not found in package")
        perl_lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        # Write a test script to avoid shell quoting issues
        test_script = os.path.join(tempfile.gettempdir(), "test_extutils_depends.pl")
        with open(test_script, "w") as f:
            f.write("use ExtUtils::Depends;\n")
            f.write("my $dep = ExtUtils::Depends->new('Test::Module');\n")
            f.write("die 'not a ExtUtils::Depends object' unless ref($dep) eq 'ExtUtils::Depends';\n")
            f.write("die 'wrong name' unless $dep->{name} eq 'Test::Module';\n")
            f.write("die 'no typemaps' unless ref($dep->{typemaps}) eq 'ARRAY';\n")
            f.write("die 'no deps' unless ref($dep->{deps}) eq 'HASH';\n")
            f.write("print \"ExtUtils::Depends test OK\\n\";\n")
        self.run('PERL5LIB="{}" perl "{}"'.format(perl_lib_dir, test_script))
