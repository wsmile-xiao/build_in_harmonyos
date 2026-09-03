#!/usr/bin/env python3
"""Conan consumer test for tinygltfloader 0.9.2."""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class TinygltfloaderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        dependency = self.dependencies["tinygltfloader"]
        include_dirs = [
            os.path.join(dependency.package_folder, include_dir)
            for include_dir in dependency.cpp_info.includedirs
        ]
        include_flags = " ".join(
            f'"-I{include_dir}"' for include_dir in include_dirs
        )
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compiler_executables.get("cpp", "clang++")
        source = os.path.join(self.source_folder, "test.cpp")
        binary = os.path.join(self.build_folder, "test_tinygltfloader")
        self.run(
            f'"{cxx}" -std=c++17 -Wall -Werror "{source}" '
            f'{include_flags} -o "{binary}"'
        )

    def test(self):
        binary = os.path.join(self.build_folder, "test_tinygltfloader")
        self.run(f'"{binary}"', env="conanrun")
