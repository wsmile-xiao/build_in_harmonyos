#!/usr/bin/env python3
"""Conan test package for libldac."""
import os

from conan import ConanFile


class LibldacTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        package = self.dependencies["libldac"].package_folder
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c", "clang")
        source = os.path.join(self.source_folder, "test_package.c")
        self.run(
            f'{compiler} "{source}" -I{package}/include -L{package}/lib '
            "-lldacBT_abr -lldacBT_enc -o test_package"
        )

    def test(self):
        self.run("./test_package", env="conanrun")
