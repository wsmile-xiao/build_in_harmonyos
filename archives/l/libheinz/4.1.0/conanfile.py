#!/usr/bin/env python3
"""Conan recipe for libheinz 4.1.0.

libheinz is a header-only C++20 base library (Complex, Vectors3D, Rotations3D)
from the Heinz Maier-Leibnitz Zentrum.  Upstream builds an INTERFACE CMake
target and ships three Catch2-based CTest programs; this recipe builds and runs
those upstream tests, then installs only the public headers and CMake config.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get


class LibheinzConan(ConanFile):
    name = "libheinz"
    version = "4.1.0"
    description = "Header-only C++ base library of Heinz Maier-Leibnitz Zentrum"
    license = "0BSD"
    homepage = "https://jugit.fz-juelich.de/mlz/libheinz"
    url = ""  # CI fills this
    topics = ("header-only", "math", "vectors", "rotations", "complex", "cpp20")
    package_type = "header-library"

    # R32: settings.os check must include both Linux and OHOS
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build the upstream Catch2 test programs so they run during conan create.
        tc.variables["BUILD_TESTING"] = True
        # The upstream enforces C++20 (concepts); disable pedantic/werror so the
        # OHOS clang toolchain is not derailed by harmless warnings.
        tc.variables["PEDANTIC"] = False
        tc.variables["WERROR"] = False
        # header-only INTERFACE target — BUILD_SHARED_LIBS is irrelevant but set
        # it OFF to avoid any shared-library machinery on OHOS.
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run the 3 upstream CTest programs (12 TEST_CASE / 114 assertions).
        ctest_env = Environment()
        ctest_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        ctest_env.define("CTEST_PARALLEL_LEVEL", "1")
        with ctest_env.vars(self).apply():
            cmake.test()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # header-only: no compiled library to link
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "LibHeinz")
        self.cpp_info.set_property("cmake_target_name", "LibHeinz::LibHeinz")
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("pkg_config_name", "libheinz")
