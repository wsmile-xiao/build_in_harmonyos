#!/usr/bin/env python3
"""Conan recipe - c-blosc 1.21.6."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
import os


class CBloscConan(ConanFile):
    name = "c-blosc"
    version = "1.21.6"
    description = "A blocking, shuffling and lossless compression library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Blosc/c-blosc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS_SKIP"] = True
        tc.variables["BUILD_SHARED"] = bool(self.options.shared)
        tc.variables["BUILD_STATIC"] = not bool(self.options.shared)
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_FUZZERS"] = False
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["DEACTIVATE_SNAPPY"] = True
        tc.variables["PREFER_EXTERNAL_LZ4"] = False
        tc.variables["PREFER_EXTERNAL_ZLIB"] = False
        tc.variables["PREFER_EXTERNAL_ZSTD"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        if str(self.settings.os) == "Windows" and not bool(self.options.shared):
            self.cpp_info.libs = ["libblosc"]
        else:
            self.cpp_info.libs = ["blosc"]
        self.cpp_info.set_property("cmake_file_name", "c-blosc")
        self.cpp_info.set_property("cmake_target_name", "c-blosc::c-blosc")
        self.cpp_info.set_property("pkg_config_name", "blosc")
