#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("c", "clang")

    def generate(self):
        runenv = VirtualRunEnv(self)
        runenv.generate()

    def build(self):
        dependency = self.dependencies["libunistring"]
        include_args = " ".join(f"-I{directory}" for directory in dependency.cpp_info.includedirs)
        libdir_args = " ".join(f"-L{directory}" for directory in dependency.cpp_info.libdirs)
        lib_args = " ".join(f"-l{lib}" for lib in dependency.cpp_info.libs)
        os.makedirs(self.build_folder, exist_ok=True)
        source = os.path.join(self.source_folder, "test.c")
        binary = os.path.join(self.build_folder, "test_libunistring")
        self.run(f"{self._compiler()} {include_args} {source} {libdir_args} {lib_args} -o {binary}")

    def test(self):
        bin_path = os.path.join(self.build_folder, "test_libunistring")
        self.run(bin_path, env="conanrun")
