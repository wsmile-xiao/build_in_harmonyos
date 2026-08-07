#!/usr/bin/env python3
"""Consumer test for Lua."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LuaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: compile and link test passed")
            return
        lua_bin = os.path.join(self.dependencies["lua"].package_folder, "bin", "lua")
        luac_bin = os.path.join(self.dependencies["lua"].package_folder, "bin", "luac")
        self.run(f'"{lua_bin}" -v', env="conanrun")
        self.run(f'"{luac_bin}" -v', env="conanrun")
        test_exe = os.path.join(self.build_folder, "test_lua")
        self.run(f'"{test_exe}"', env="conanrun")
