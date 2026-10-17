#!/usr/bin/env python3
"""Conan recipe for Matplot++ 1.2.2.

Builds the static plotting library for Linux and OHOS consumers.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, collect_libs, copy, export_conandata_patches, get


class MatplotplusplusConan(ConanFile):
    name = "matplotplusplus"
    version = "1.2.2"
    description = "C++ graphics library for data visualization"
    license = "MIT"
    homepage = "https://github.com/alandefreitas/matplotplusplus"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Matplot++ supports Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["MATPLOTPP_BUILD_EXAMPLES"] = False
        tc.variables["MATPLOTPP_BUILD_TESTS"] = True
        tc.variables["MATPLOTPP_BUILD_INSTALLER"] = True
        tc.variables["MATPLOTPP_BUILD_PACKAGE"] = False
        tc.variables["MATPLOTPP_BUILD_WITH_PEDANTIC_WARNINGS"] = False
        tc.variables["MATPLOTPP_BUILD_WITH_SANITIZERS"] = False
        tc.variables["MATPLOTPP_BUILD_SHARED_LIBS"] = False
        tc.variables["MATPLOTPP_BUILD_EXPERIMENTAL_OPENGL_BACKEND"] = False
        tc.variables["MATPLOTPP_BUILD_HIGH_RESOLUTION_WORLD_MAP"] = False
        tc.variables["MATPLOTPP_WITH_OPENCV"] = False
        tc.variables["MATPLOTPP_WITH_SYSTEM_CIMG"] = False
        tc.variables["MATPLOTPP_WITH_SYSTEM_NODESOUP"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.build(target="generate_examples")

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["matplot"]
        self.cpp_info.set_property("cmake_file_name", "matplotplusplus")
        self.cpp_info.set_property("cmake_target_name", "matplotplusplus::matplotplusplus")
        self.cpp_info.system_libs = ["m"] if self.settings.os == "OHOS" else ["m", "pthread", "dl"]
