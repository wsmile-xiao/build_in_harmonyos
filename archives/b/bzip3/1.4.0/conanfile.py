#!/usr/bin/env python3
"""Conan recipe for bzip3 1.4.0 — CMake build system."""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Bzip3Conan(ConanFile):
    name = "bzip3"
    version = "1.4.0"
    description = "A better and stronger spiritual successor to BZip2"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/kspalaiologos/bzip3"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BZIP3_BUILD_APPS"] = "ON"
        tc.variables["BZIP3_ENABLE_PTHREAD"] = "ON"
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
        self.cpp_info.set_property("cmake_file_name", "bzip3")
        self.cpp_info.set_property("cmake_target_name", "bzip3::bz3")
        self.cpp_info.set_property("pkg_config_name", "bzip3")
        self.cpp_info.libs = ["bzip3"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.bindirs = ["bin"]
