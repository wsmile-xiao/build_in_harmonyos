#!/usr/bin/env python3
"""Conan test_package for LibRHash 1.4.4."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibRHashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _compiler_executable(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if compilers:
            return compilers.get("c", "clang")
        return "clang"

    def build(self):
        dep = self.dependencies["librhash"]
        include_flags = " ".join(f"-I{path}" for path in dep.cpp_info.includedirs)
        libdir_flags = " ".join(f"-L{path}" for path in dep.cpp_info.libdirs)
        lib_flags = " ".join(f"-l{lib}" for lib in dep.cpp_info.libs)
        source = os.path.join(self.source_folder, "test.c")
        self.run(f"{self._compiler_executable()} {source} {include_flags} {libdir_flags} {lib_flags} -o test_librhash")

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.build_folder, "test_librhash"), env="conanrun")
