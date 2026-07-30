#!/usr/bin/env python3
"""Consumer test for lua-luv."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LuaLuvTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # CMakeDeps generates config files only for direct test requirements.
        self.requires("lua/5.4.8")
        self.requires("libuv/1.52.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = self.dependencies["lua-luv"].package_folder
        module = os.path.join(package, "lib", "lua", "5.4", "luv.so")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_lua_luv")
        self.run(f'"{test_bin}" "{module}"', env="conanrun")
