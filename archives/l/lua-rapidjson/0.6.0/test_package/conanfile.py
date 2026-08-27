#!/usr/bin/env python3
"""Conan test_package for lua-rapidjson — exercises the rapidjson Lua module."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.4.8")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Get the lib directory from lua-rapidjson dependency
        lua_rapidjson = self.dependencies["lua-rapidjson"].cpp_info
        tc.variables["RAPIDJSON_LIB_DIR"] = lua_rapidjson.libdirs[0]
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_lua_rapidjson")
        self.run(cmd, env="conanrun")
