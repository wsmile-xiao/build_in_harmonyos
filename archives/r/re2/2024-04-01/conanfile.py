#!/usr/bin/env python3
"""Conan recipe for re2 2024-04-01 (CMake).

re2 is Google's regular expression library, written in C++.
It depends on abseil-cpp for synchronization primitives, string formatting,
and hash containers.

The abseil-cpp conan recipe uses cmake_file_name="abseil-cpp", but re2's
CMakeLists.txt calls find_package(absl REQUIRED) and links against
individual absl::* targets (absl::base, absl::strings, etc.).  The
abseil-cpp binary package ships the original abslConfig.cmake at
lib/cmake/absl/ which provides those targets.  We set absl_DIR to that
path so CMake finds the real abseil config instead of the conan-generated
one (same pattern used by protobuf/33.6 in this repo).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Re2Conan(ConanFile):
    name = "re2"
    version = "2024-04-01"
    description = "Google's regular expression library, written in C++"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/re2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["RE2_BUILD_TESTING"] = False

        # Point find_package(absl) to the real abseil-cpp cmake config
        # (lib/cmake/absl/abslConfig.cmake) which provides individual
        # absl::* targets that re2's CMakeLists.txt links against.
        tc.variables["absl_DIR"] = os.path.join(
            self.dependencies["abseil-cpp"].package_folder,
            "lib",
            "cmake",
            "absl",
        ).replace("\\", "/")
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
        self.cpp_info.set_property("cmake_file_name", "re2")
        self.cpp_info.set_property("cmake_target_name", "re2::re2")
        self.cpp_info.libs = ["re2"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.requires = ["abseil-cpp::abseil-cpp"]
