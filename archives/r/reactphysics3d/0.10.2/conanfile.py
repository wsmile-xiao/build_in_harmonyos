#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Reactphysics3D, reactphysics3d, 0.10.2, ReactPhysics3D physics engine, MIT, https://www.reactphysics3d.com
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Reactphysics3DConan(ConanFile):
    name = "reactphysics3d"
    version = "0.10.2"
    description = "ReactPhysics3D physics engine"
    license = "MIT"
    homepage = "https://www.reactphysics3d.com"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # All dependencies MUST use @ohpcd/stable format (R27)
        # self.requires("openssl/1.1.1w@ohpcd/stable")
        # self.requires("zlib/1.3.1@ohpcd/stable")
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # ReactPhysics3D-specific build options:
        # library only, no testbed/demos/docs/tests in the packaged build
        tc.variables["RP3D_COMPILE_LIBRARY"] = "ON"
        tc.variables["RP3D_COMPILE_TESTBED"] = "OFF"
        tc.variables["RP3D_COMPILE_TESTS"] = "OFF"
        tc.variables["RP3D_PROFILING_ENABLED"] = "OFF"
        tc.variables["RP3D_GENERATE_DOCUMENTATION"] = "OFF"
        tc.variables["RP3D_CODE_COVERAGE_ENABLED"] = "OFF"
        tc.variables["RP3D_DOUBLE_PRECISION_ENABLED"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["reactphysics3d"]
        # Upstream installs a CMake package config (ReactPhysics3DConfig.cmake)
        self.cpp_info.set_property("cmake_file_name", "ReactPhysics3D")
        self.cpp_info.set_property("cmake_target_name", "reactphysics3d")
