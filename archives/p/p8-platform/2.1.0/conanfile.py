#!/usr/bin/env python3
"""Conan recipe for p8-platform 2.1.0 — Pulse-Eight platform support library."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class P8PlatformConan(ConanFile):
    name = "p8-platform"
    version = "2.1.0"
    description = "Platform support library for Pulse-Eight projects"
    license = "GPL-2.0"
    homepage = "https://github.com/Pulse-Eight/platform"

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
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # CMake 4.x removed compatibility with cmake_minimum_required < 3.5
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake doesn't have HarmonyOS platform module, use Linux
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
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
        self.cpp_info.libs = ["p8-platform"]
