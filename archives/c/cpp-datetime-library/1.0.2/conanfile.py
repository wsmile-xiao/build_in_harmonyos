#!/usr/bin/env python3
"""Conan recipe — cpp-datetime-library 1.0.2 (CMake project).

Cross-platform C++ date/time library (jed_utils namespace).
CMake build; produces a static/shared library libdatetime plus headers.
Upstream tests use googletest downloaded at configure time; on OHOS the
network fetch is unavailable, so BUILD_TESTING is disabled in the recipe
and upstream tests are run separately (see reports).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
import os


class CppDatetimeLibraryConan(ConanFile):
    name = "cpp-datetime-library"
    version = "1.0.2"
    description = "A cross-platform DateTime library written in C++"
    license = "MIT"
    homepage = "https://github.com/jeremydumais/CPP-DateTime-library"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: OHOS is treated as Linux-compatible; upstream CMake does not
        # know OHOS, so map to Linux for CMake's platform detection.
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream fetches googletest via ExternalProject at configure time;
        # disable to keep the recipe network-free. Tests are run separately.
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Upstream installs lib to lib/datetime/ and headers to include/datetime/
        self.cpp_info.libs = ["datetime"]
        self.cpp_info.libdirs = ["lib/datetime"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "datetime")
        self.cpp_info.set_property("cmake_target_name", "datetime::datetime")
