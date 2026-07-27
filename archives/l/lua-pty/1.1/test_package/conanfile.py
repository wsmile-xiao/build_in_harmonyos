#!/usr/bin/env python3
"""Test package for lua-pty 1.1 — verifies pty.core module loads and getenvs() returns a table."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LuaPtyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        # Get the package's lib directory to find core.so
        pkg = self.dependencies["lua-pty"]
        libdir = pkg.cpp_info.libdirs[0] if pkg.cpp_info.libdirs else ""
        so_path = os.path.join(libdir, "lua/5.4/pty/core.so") if libdir else ""

        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_lua_pty")
        self.run(f'"{test_bin}" "{so_path}"')
