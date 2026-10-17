#!/usr/bin/env python3
"""Conan test_package for perl-file-remove 1.61.

R34 real consumer check: loads the packaged File::Remove via PERL5LIB and
exercises the actual remove()/rm() API against a freshly created temp
directory tree, asserting that files/dirs no longer exist afterwards
(not a print-only / pass-only shell test).
"""
import os

from conan import ConanFile


class PerlFileRemoveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_perl_lib(self):
        """Perl lib dir inside the installed perl-file-remove package."""
        dep = self.dependencies["perl-file-remove"]
        return os.path.join(dep.package_folder, "lib", "perl5")

    def test(self):
        perl_lib = self._find_perl_lib()
        test_script = os.path.join(self.recipe_folder, "run_test.sh")
        self.run(f'sh "{test_script}" "{perl_lib}"', env="conanrun")
