#!/usr/bin/env python3
"""Conan recipe for aces_container 1.0.2."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class AcesContainerConan(ConanFile):
    name = "aces_container"
    version = "1.0.2"
    description = "C++ reference writer for SMPTE S2065-4 ACES image container files"
    license = "LicenseRef-Academy-Adobe-RSA"
    homepage = "https://github.com/aces-aswf/aces_container"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "aces_container")
        self.cpp_info.set_property("cmake_target_name", "aces_container::aces_container")
        self.cpp_info.set_property("pkg_config_name", "aces_container")
        self.cpp_info.libs = ["AcesContainer"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "aces")]
