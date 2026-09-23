#!/usr/bin/env python3
"""Conan recipe for nuspell 5.1.8.

Nuspell is a fast and safe spelling checker library, designed as a
modern C++ replacement for Hunspell. It supports Hunspell-compatible
dictionaries and provides full Unicode support via ICU.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps


class NuspellConan(ConanFile):
    name = "nuspell"
    version = "5.1.8"
    description = "Nuspell - fast and safe spelling checker library (Hunspell replacement)"
    license = "LGPL-3.0-or-later"
    homepage = "https://nuspell.github.io/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("icu4c/77")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        target_os = str(self.settings.os)
        if target_os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_TOOLS"] = "ON"
        tc.variables["BUILD_DOCS"] = "OFF"
        tc.generate()
        # CMakeDeps generates icu4cConfig.cmake with target icu4c::icu4c
        # Patch changes upstream find_package(ICU) -> find_package(icu4c) and ICU::uc -> icu4c::icu4c
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["nuspell"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "Nuspell")
        self.cpp_info.set_property("cmake_target_name", "Nuspell::nuspell")
        self.cpp_info.set_property("pkg_config_name", "nuspell")
        self.cpp_info.requires = ["icu4c::icu4c"]
