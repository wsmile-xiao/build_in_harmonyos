#!/usr/bin/env python3
"""Conan test package for the SPIRV-Cross C API and CLI."""
import os

from conan import ConanFile


class SpirvCrossTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        package = self.dependencies["spirv-cross"].package_folder
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("cpp", "clang++")
        source = os.path.join(self.source_folder, "test_package.cpp")
        self.run(
            f'{compiler} "{source}" -I{package}/include -L{package}/lib '
            "-lspirv-cross-c -lspirv-cross-cpp -lspirv-cross-reflect "
            "-lspirv-cross-msl -lspirv-cross-hlsl -lspirv-cross-glsl "
            "-lspirv-cross-util -lspirv-cross-core -lc++ -lc++abi -o test_package"
        )

    def test(self):
        package = self.dependencies["spirv-cross"].package_folder
        cli = os.path.join(package, "bin", "spirv-cross")
        self.run("./test_package", env="conanrun")
        self.run(
            f'"{cli}" minimal.spv --output minimal.glsl && '
            'grep -q "void main" minimal.glsl',
            env="conanrun",
        )
