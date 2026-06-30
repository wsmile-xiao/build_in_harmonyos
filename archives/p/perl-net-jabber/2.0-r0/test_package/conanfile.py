#!/usr/bin/env python3
"""Conan test_package for perl-net-jabber — Perl L1 test.

Verifies that the installed Net::Jabber module can be loaded
and basic Jabber protocol objects can be created.
"""
import os

from conan import ConanFile


class PerlNetJabberTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # PERL5LIB is set by runenv_info from the package's package_info()
        test_script = os.path.join(self.recipe_folder, "test.pl")
        self.run(f'perl "{test_script}"', env="conanrun")
