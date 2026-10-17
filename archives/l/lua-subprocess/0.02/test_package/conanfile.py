#!/usr/bin/env python3
"""Conan test_package for lua-subprocess 0.02.

This test compiles a C program that embeds Lua, sets the Lua C path
to include the built subprocess.so, and runs a Lua script that uses
the subprocess module to spawn a process and verify its output.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LuaSubprocessTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.4.8")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Get the directory containing subprocess.so from the built package
        subprocess_pkg = self.dependencies["lua-subprocess"]
        subprocess_libdir = os.path.join(subprocess_pkg.package_folder, "lib", "lua", "5.4")

        # Set LUA_CPATH so Lua can find subprocess.so
        # Pattern: <libdir>/?.so — Lua replaces ? with the module name
        lua_cpath = os.path.join(subprocess_libdir, "?.so") + ";;"
        os.environ["LUA_CPATH"] = lua_cpath

        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_subprocess"),
            env="conanrun",
        )
