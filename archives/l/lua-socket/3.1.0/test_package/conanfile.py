#!/usr/bin/env python3
"""Consumer test for lua-socket.

Builds a small C program that embeds Lua, sets package.path/package.cpath
to point at the installed lua-socket package, then runs a Lua script that
requires "socket" and "mime" and exercises basic APIs.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LuaSocketTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # CMakeDeps needs the lua target for linking the embedded interpreter.
        self.requires("lua/5.4.8")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = self.dependencies["lua-socket"].package_folder
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_lua_socket")
        self.run(f'"{test_bin}" "{package}"', env="conanrun")
