#!/usr/bin/env python3
"""Conan recipe — maddy 1.6.0 (CMake header-only / INTERFACE library).

maddy: C++20 markdown-to-HTML parser library (header-only, INTERFACE target).
Upstream builds with:
  cmake -S . -B build -DMADDY_BUILD_WITH_TESTS=ON && cmake --build build

Downstream expects:
  find_package(maddy REQUIRED)
  target_link_libraries(... PRIVATE maddy::maddy)

R32: settings.os check accepts both Linux and OHOS.
R26: header-only library — no runtime .so, bindirs/libdirs empty.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MaddyConan(ConanFile):
    name = "maddy"
    version = "1.6.0"
    description = "C++20 library for parsing Markdown into HTML (header-only)"
    license = "MIT"
    homepage = "https://github.com/progsource/maddy"
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
        # R32: platform check must accept OHOS
        if self.settings.os in ("Linux", "OHOS"):
            # Some CMake versions do not treat OHOS as a known system name
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            # Conan arch is "armv8"; CMake expects "aarch64"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Upstream enables install for the main project via GNUInstallDirs
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        # Header-only: no compiled artifacts
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]

        # Upstream installs maddyConfig.cmake + maddyTargets.cmake with
        # namespace maddy::maddy (INTERFACE target)
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_file_name", "maddy")
        self.cpp_info.set_property("cmake_target_name", "maddy::maddy")
        self.cpp_info.builddirs.append(
            os.path.join("lib", "cmake", "maddy")
        )