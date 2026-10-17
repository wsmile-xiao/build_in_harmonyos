#!/usr/bin/env python3
"""Conan test_package — lutok 0.6.2 consumer test (Conan L1).

Builds a real consumer against the installed package: creates a Lua state,
evaluates Lua code through lutok::do_string, binds a native C++ function via
lutok::create_module, checks the RAII stack_cleaner, verifies that a failing
script raises lutok::error and reaches the raw lua_State through
lutok::state_c_gate (which also covers the packaged lua.hpp wrapper header).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LutokTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_lutok")
        self.run(executable, env="conanrun")
