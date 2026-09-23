#!/usr/bin/env python3
"""Conan recipe for boxed-cpp 1.4.3.

boxed-cpp is a small header-only C++20 library (``include/boxed-cpp/boxed.hpp``)
for boxing primitive types into distinct strong types, to avoid easily
swappable parameters. It ships a CMake INTERFACE target (``boxed-cpp::boxed-cpp``)
plus a CMake package config so downstream ``find_package(boxed-cpp)`` works.

Header-only, so the package installs the header and the CMake config files
produced by the upstream ``install()`` rules; there is no compiled artifact.
Upstream unit tests (15 TEST_CASEs in test-boxed-cpp.cpp) are built on
Catch2 v3.4.0. They were executed on device during adaptation against the
official v1.4.3 tag (see notes.md / PR); the recipe itself keeps the library
dependency-free and does not pull Catch2, which is not yet published on the
OHOS artifact repository (only Catch2 v2.13.10-r0 is).
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class BoxedCppConan(ConanFile):
    name = "boxed-cpp"
    version = "1.4.3"
    description = "C++20 header-only library for boxing primitive types (strong typedefs)"
    license = "Apache-2.0"
    homepage = "https://github.com/contour-terminal/boxed-cpp"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/b/boxed-cpp/1.4.3"
    topics = ("boxing", "strong-types", "header-only", "cpp20")
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # header-only: identical content for every configuration
        self.info.clear()

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BOXED_TESTING"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # BOXED_TESTING=OFF (set in generate()) keeps the build free of the
        # Catch2 v3 dependency; this is an INTERFACE library so there is no
        # compiled artifact. configure() still generates the CMake package
        # config files that package() installs.
        cmake = CMake(self)
        cmake.configure()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        # INTERFACE library, nothing to link; consumers just include boxed.hpp.
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "boxed-cpp")
        self.cpp_info.set_property("cmake_target_name", "boxed-cpp::boxed-cpp")
        self.cpp_info.components["boxed-cpp"].set_property("cmake_target_name", "boxed-cpp::boxed-cpp")
