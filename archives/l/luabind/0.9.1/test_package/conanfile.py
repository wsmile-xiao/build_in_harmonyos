#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake import CMakeDeps


class LuabindTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # lua/5.1.5 and boost/1.90.0 packages do not export include dirs via
        # CMakeDeps; propagate the actual include paths so consumers can see
        # lua.h / boost/config.hpp (luabind public headers include both).
        lua = self.dependencies["lua"]
        boost = self.dependencies["boost"]
        tc.variables["LUA_INCLUDE_DIR"] = os.path.join(lua.package_folder, "include")
        tc.variables["BOOST_INCLUDE_DIR"] = os.path.join(boost.package_folder, "include")
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"), env="conanrun")