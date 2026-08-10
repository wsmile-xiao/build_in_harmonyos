#!/usr/bin/env python3
"""Test package for lua-tableshape — verifies module loads and basic shape checking works."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LuaTableshapeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.4.8")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # Resolve the tableshape module directory from the package.
        pkg = self.dependencies["lua-tableshape"]
        module_dir = os.path.join(pkg.package_folder, "res", "share", "lua", "5.4")
        cmake.configure(variables={"TABLESHAPE_MODULE_DIR": module_dir})
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: compile and link test passed")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_tableshape")
        self.run(f'"{test_bin}"', env="conanrun")
