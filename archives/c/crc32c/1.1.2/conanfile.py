#!/usr/bin/env python3
"""Conan recipe - crc32c 1.1.2."""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, valid_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir, apply_conandata_patches, export_conandata_patches
import os


class Crc32cConan(ConanFile):
    name = "crc32c"
    version = "1.1.2"
    description = "CRC32C implementation with support for CPU-specific acceleration instructions"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/crc32c"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    @property
    def _min_cppstd(self):
        return "11"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS", "Windows", "Macos", "Android", "iOS"):
            raise ConanInvalidConfiguration(
                f"crc32c does not support OS: {self.settings.os}"
            )
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if not valid_min_cppstd(self, self._min_cppstd):
            tc.variables["CMAKE_CXX_STANDARD"] = self._min_cppstd
        # CMake 4.x compatibility: crc32c requires cmake_minimum_required(VERSION 3.1)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Disable optional glog dependency
        tc.variables["CRC32C_USE_GLOG"] = False
        # Disable tests and benchmarks (require googletest/benchmark submodules)
        tc.variables["CRC32C_BUILD_TESTS"] = False
        tc.variables["CRC32C_BUILD_BENCHMARKS"] = False
        # Enable install targets
        tc.variables["CRC32C_INSTALL"] = True
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Crc32c")
        self.cpp_info.set_property("cmake_target_name", "Crc32c::crc32c")
        self.cpp_info.libs = ["crc32c"]
