#!/usr/bin/env python3
"""Conan test package for Berkeley SoftFloat."""

from os.path import join

from conan import ConanFile
from conan.tools.build import can_run


class SoftfloatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        package = self.dependencies["softfloat"].package_folder
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        source = join(self.source_folder, "test.c")
        binary = join(self.build_folder, "test_softfloat")
        self.run(
            f'"{cc}" -std=c99 -I"{join(package, "include")}" '
            f'"{source}" "{join(package, "lib", "libsoftfloat.a")}" -o "{binary}"'
        )

    def test(self):
        if can_run(self):
            self.run(f'"{join(self.build_folder, "test_softfloat")}"')
