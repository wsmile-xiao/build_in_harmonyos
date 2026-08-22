#!/usr/bin/env python3
"""Test package for lua-toml 1.0.

Creates a C test program that links against liblua (from the lua
conan dependency) and uses the Lua C API to load toml.lua, then
verifies parse and encode functionality.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import copy


class LuaTomlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Direct lua dependency so CMakeDeps generates find_package(lua)
        self.requires("lua/5.4.8")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        # Copy toml.lua into the build folder so the test binary
        # can find it via package.path = "./?.lua;"
        lua_toml = self.dependencies["lua-toml"]
        src_dir = os.path.join(lua_toml.package_folder, "share", "lua", "5.4")
        copy(self, "toml.lua", src=src_dir, dst=self.build_folder)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("./test_lua_toml", env="conanrun")
