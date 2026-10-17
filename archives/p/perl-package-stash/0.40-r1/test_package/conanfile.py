#!/usr/bin/env python3
"""Conan test_package for perl-package-stash — L1 smoke test.

Verifies that Package::Stash can be loaded and basic stash operations work.
Tests real API: new, add_symbol, get_symbol, has_symbol, remove_symbol,
list_all_symbols, get_all_symbols, get_or_add_symbol, name, namespace.
"""
import os

from conan import ConanFile


class PerlPackageStashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.recipe_folder, "test_stash.sh")
        self.run(f'sh "{test_script}"', env="conanrun")
