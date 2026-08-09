#!/usr/bin/env python3
"""Consumer and fault-injection tests for acf-lib-lua5.5 0.11.1."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class AcfLibLua55TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.5.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dependency = self.dependencies["acf-lib-lua5.5"]
        root = os.path.join(dependency.package_folder, dependency.cpp_info.resdirs[0])
        packaged_lua = sum(
            filename.endswith(".lua")
            for _, _, files in os.walk(root)
            for filename in files
        )
        if packaged_lua != 16:
            raise ConanException(
                f"Expected 16 packaged Lua entries, found {packaged_lua}"
            )
        if not can_run(self):
            self.output.info(
                "Cross-built acf_lib_probe; run both scenarios with the packaged "
                "Lua modules on the HarmonyOS PC emulator."
            )
            return

        executable = os.path.join(self.cpp.build.bindir, "acf_lib_probe")
        self.run(f'"{executable}" "{root}"', env="conanrun")
        self.run(f'"{executable}" --expect-invalid "{root}"', env="conanrun")
