#!/usr/bin/env python3
"""Conan recipe for cppp-reiconv 3.0.0 (CMake build).

cppp-reiconv is a C/C++ character set conversion library. Per the official
README, building requires two sibling repositories from the same org:
  - build-aux      (CMake build helpers, provides cppp_build_library)
  - cppp-platform  (platform abstraction, add_subdirectory'd by CMakeLists)
Both are fetched at pinned commits from the official codeload URLs.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CpppReiconvConan(ConanFile):
    name = "cppp-reiconv"
    version = "3.0.0"
    description = "A character set conversion library based on GNU LIBICONV (C++ Plus Project)."
    license = "LGPL-3.0"
    homepage = "https://github.com/cppp-project/cppp-reiconv"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Main source tarball (official v3.0.0 tag).
        get(self, **self.conan_data["sources"]["reiconv"], strip_root=True,
            filename="cppp-reiconv-3.0.0.tar.gz")
        # Required build-time siblings (official repos, pinned commits).
        get(self, **self.conan_data["sources"]["build_aux"], strip_root=True, destination="build-aux",
            filename="build-aux.tar.gz")
        get(self, **self.conan_data["sources"]["cppp_platform"], strip_root=True, destination="cppp-platform",
            filename="cppp-platform.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: default to static for library packages.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
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
        self.cpp_info.libs = ["cppp-reiconv"]
