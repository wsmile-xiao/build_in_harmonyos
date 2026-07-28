#!/usr/bin/env python3
"""Conan 2 recipe for argtable3 3.3.1."""

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class Argtable3Conan(ConanFile):
    name = "argtable3"
    version = "3.3.1"
    description = "ANSI C command-line parsing library"
    license = "BSD-3-Clause"
    homepage = "https://www.argtable.org"
    url = "https://github.com/argtable/argtable3"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = False
        toolchain.variables["ARGTABLE3_ENABLE_TESTS"] = True
        toolchain.variables["ARGTABLE3_ENABLE_EXAMPLES"] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not cross_building(self):
            self.run(
                f'ctest --test-dir "{self.build_folder}" --output-on-failure'
            )

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["argtable3"]
        if str(self.settings.os) != "Windows":
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "argtable3")
        self.cpp_info.set_property(
            "cmake_target_name", "argtable3::argtable3"
        )
        self.cpp_info.set_property("pkg_config_name", "argtable3")
