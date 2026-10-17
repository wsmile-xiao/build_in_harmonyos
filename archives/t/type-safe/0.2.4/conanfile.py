#!/usr/bin/env python3
"""Conan recipe for type-safe 0.2.4, a header-only CMake C++ library."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class TypeSafeConan(ConanFile):
    name = "type-safe"
    version = "0.2.4"
    description = "Zero-overhead C++ abstractions using the type system to prevent bugs"
    license = "Zlib"
    homepage = "https://github.com/foonathan/type_safe"
    url = "https://github.com/foonathan/type_safe"
    topics = ("type-safe", "header-only", "c++", "strong-types")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4 rejects the old minimum version in the vendored
        # debug_assert subproject unless this compatibility policy is set.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Build the complete upstream test and example targets in build().
        tc.cache_variables["TYPE_SAFE_BUILD_TEST_EXAMPLE"] = True
        tc.cache_variables["TYPE_SAFE_BUILD_DOC"] = False
        tc.cache_variables["TYPE_SAFE_IMPORT_STD_MODULE"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # The upstream Catch2 suite is part of the package's build-time gate.
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # type_safe's headers include <debug_assert.hpp>.  The upstream CMake
        # install omits the vendored dependency when no external package is
        # found, so carry that single header in this self-contained package.
        copy(
            self,
            "debug_assert.hpp",
            src=os.path.join(self.source_folder, "external", "debug_assert"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "type_safe")
        self.cpp_info.set_property("cmake_target_name", "type_safe::type_safe")
