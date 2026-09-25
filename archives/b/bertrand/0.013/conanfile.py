#!/usr/bin/env python3
"""Conan recipe — bertrand 0.013 (C++17 header-only design-by-contract).

bertrand is a minimalistic, header-only implementation of design by contract
(DbC) for C++: Require/Ensure/Invariant macros plus a bertrand::find value
membership helper. It is an INTERFACE cmake library: nothing is compiled,
the public header include/bertrand/bertrand.hpp is installed together with
the upstream CMake package config (bertrandConfig.cmake + Targets, target
bertrand::bertrand).

Tests are kept OFF in this recipe (BUILD_TESTING=OFF): the upstream test
subdirectory requires Catch2 via a network-downloaded conan.cmake module;
the PR declares the upstream test enumeration in test_package/MANIFEST.yml.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BertrandConan(ConanFile):
    name = "bertrand"
    version = "0.013"
    description = "A minimalistic, header-only implementation of design by contract for C++"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/bernedom/bertrand"
    url = "https://github.com/bernedom/bertrand"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only library, no runtime or build dependencies
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # INTERFACE library: nothing to compile, tests stay OFF
        # (upstream test dir needs Catch2 + a network-downloaded conan.cmake)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BERTRAND_BUILD_TESTING"] = "OFF"
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
        # header-only: headers + CMake config installed, no libs to link
        self.cpp_info.set_property("cmake_file_name", "bertrand")
        self.cpp_info.set_property("cmake_target_name", "bertrand::bertrand")