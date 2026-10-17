#!/usr/bin/env python3
"""Conan test_package for php83-pecl-timezonedb.

Tests that the timezonedb.so shared library is a valid PHP extension
by verifying it exists as an ELF shared object and exports the
get_module symbol (standard PHP extension entry point).
"""
import os

from conan import ConanFile
from conan.tools.gnu import AutotoolsToolchain


class Php83PeclTimezonedbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # Compile a small C program that reads the .so file and
        # checks ELF magic + searches for get_module in symbol table
        so_path = os.path.join(
            self.dependencies["php83-pecl-timezonedb"].package_folder,
            "lib", "php", "extensions", "timezonedb.so"
        )
        self.run(
            f'$CC -DSO_PATH=\\"{so_path}\\" '
            f'-o test_timezonedb {os.path.join(self.source_folder, "test.c")}',
            env="conanbuild"
        )

    def test(self):
        self.run('./test_timezonedb', env="conanrun")
