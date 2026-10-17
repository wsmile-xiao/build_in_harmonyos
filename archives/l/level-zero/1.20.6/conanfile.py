#!/usr/bin/env python3
"""Conan CMake recipe for Intel oneAPI Level Zero API (level-zero) 1.20.6."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LevelZeroConan(ConanFile):
    name = "level-zero"
    version = "1.20.6"
    description = "Intel oneAPI Level Zero API - open standards-based unified API for HPC/AI accelerators"
    license = "MIT"
    homepage = "https://github.com/oneapi-src/level-zero"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"level-zero supports Linux and OHOS targets, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["BUILD_L0_LOADER_TESTS"] = False
        tc.cache_variables["SYSTEM_SPDLOG"] = False
        tc.cache_variables["INSTALL_NULL_DRIVER"] = False
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ze_loader"]
        self.cpp_info.set_property("cmake_file_name", "level-zero")
        self.cpp_info.set_property("cmake_target_name", "level-zero::level-zero")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("dl")
            self.cpp_info.system_libs.append("pthread")
