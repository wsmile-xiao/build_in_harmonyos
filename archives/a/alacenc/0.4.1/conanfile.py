#!/usr/bin/env python3
"""Conan recipe for alacenc 0.4.1."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class AlacencConan(ConanFile):
    name = "alacenc"
    version = "0.4.1"
    description = "Command-line Apple Lossless Audio Codec encoder"
    license = ("MIT", "Apache-2.0", "APSL-2.0", "BSL-1.0")
    homepage = "https://github.com/flacon/alacenc"
    url = "https://github.com/flacon/alacenc"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS", "Windows"):
            raise ConanInvalidConfiguration("alacenc supports Linux, OHOS, and Windows targets")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        tc.cache_variables["WITH_TESTS"] = False
        tc.cache_variables["WITH_EXAMPLE"] = False
        tc.cache_variables["USE_BOOST_REGEX"] = False
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_CXX_FLAGS"] = "-stdlib=libc++"
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-lc++ -lpthread"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        license_dir = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE", self.source_folder, os.path.join(license_dir, "alacenc"))
        copy(self, "LICENSE", os.path.join(self.source_folder, "vendor", "alac"), os.path.join(license_dir, "alac"))
        copy(self, "APPLE_LICENSE.txt", os.path.join(self.source_folder, "vendor", "alac", "codec"), os.path.join(license_dir, "alac"))
        copy(self, "LICENSE-MIT", os.path.join(self.source_folder, "vendor", "docopt"), os.path.join(license_dir, "docopt"))
        copy(self, "LICENSE-Boost-1.0", os.path.join(self.source_folder, "vendor", "docopt"), os.path.join(license_dir, "docopt"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
