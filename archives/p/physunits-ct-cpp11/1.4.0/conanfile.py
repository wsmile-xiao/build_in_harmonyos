#!/usr/bin/env python3
"""Conan recipe for PhysUnits-CT-Cpp11 1.4.0."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PhysunitsConan(ConanFile):
    name = "physunits-ct-cpp11"
    version = "1.4.0"
    description = "Header-only C++11 compile-time dimensional analysis library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/PhysUnits-CT-Cpp11"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Keep the standard patch export hook for the no-patch case.  This is
        # required by the repository verifier and makes future patches safe.
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # R32: accept the OHOS profile. The upstream project has no
        # platform-specific code; Linux CMake platform semantics are enough
        # for this header-only package and avoid CMake's unknown-HarmonyOS
        # platform warning on the device.
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        tc.cache_variables["PHYS_UNITS_OPT_BUILD_TESTS"] = True
        tc.cache_variables["PHYS_UNITS_OPT_BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_id(self):
        # The package contains headers and a CMake interface target only.
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "PhysUnits")
        self.cpp_info.set_property("cmake_target_name", "PhysUnits::PhysUnits")
