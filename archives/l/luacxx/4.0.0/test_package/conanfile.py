#!/usr/bin/env python3
"""Conan test_package for luacxx 4.0.0.

Consumer validation: links the installed luacxx library, includes only the
public headers (luacxx/*.hpp), and exercises real public API (Lua state
creation, value push/get, C++ function registration and Lua round-trip).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LuacxxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # luacxx's public headers include <lua.hpp>, which needs the Lua C
        # headers; expose the lua package include dir explicitly.
        self.requires("lua/5.4.8")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        lua = self.dependencies["lua"].cpp_info
        tc.variables["LUA_INCLUDE_DIR"] = lua.includedirs[0]
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_luacxx")
        self.run(f'"{bin_path}"', env="conanrun")