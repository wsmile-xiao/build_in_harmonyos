#!/usr/bin/env python3
"""Conan recipe — tsl-hopscotch-map 2.4.0 (CMake header-only / INTERFACE library).

Downstream expects:
  find_package(tsl-hopscotch-map REQUIRED)
  target_link_libraries(... PRIVATE tsl::hopscotch_map)

Header-only: no compiled artifacts, installs include/tsl/*.h + CMake config.
Reference: archives/r/robin-map/1.4.1/ (header-only CMake pattern).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TslHopscotchMapConan(ConanFile):
    name = "tsl-hopscotch-map"
    version = "2.4.0"
    description = "C++ fast hash map and hash set using hopscotch hashing (Tessil)"
    license = "MIT"
    homepage = "https://github.com/Tessil/hopscotch-map"
    url = ""  # CI fills this

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
        # R32: accept OHOS as a Linux-family platform; upstream CMake has no OHOS-specific logic
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            # Conan arch is "armv8"; CMake expects "aarch64"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
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
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "tsl-hopscotch-map")
        self.cpp_info.set_property("cmake_target_name", "tsl::hopscotch_map")
        self.cpp_info.components["hopscotch_map"].set_property(
            "cmake_target_name", "tsl::hopscotch_map"
        )
