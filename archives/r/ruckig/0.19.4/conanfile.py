#!/usr/bin/env python3
"""Conan recipe - Ruckig 0.19.4 (CMake C++ library)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class RuckigConan(ConanFile):
    name = "ruckig"
    version = "0.19.4"
    description = "Real-time jerk-constrained time-optimal trajectory generation"
    license = "MIT"
    homepage = "https://ruckig.com"
    url = "https://github.com/pantor/ruckig"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_CXX_EXTENSIONS"] = True
        tc.variables["BUILD_EXAMPLES"] = True
        tc.variables["BUILD_TESTS"] = True
        tc.variables["BUILD_BENCHMARK"] = True
        tc.variables["BUILD_PYTHON_MODULE"] = False
        tc.variables["BUILD_CLOUD_CLIENT"] = False
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # CTest covers the configured upstream test entry. The direct run uses
        # the same 5,000,000-trajectory workload as upstream GitHub Actions.
        cmake.test()
        suffix = ".exe" if self.settings.os == "Windows" else ""
        binary_dir = self.build_folder
        test_binary = os.path.join(binary_dir, "test-target" + suffix)
        self.run(f'"{test_binary}" 5000000')

        for example in (
            "01_position",
            "02_position_offline",
            "05_velocity",
            "06_stop",
            "07_minimum_duration",
            "09_dynamic_dofs",
        ):
            binary = os.path.join(binary_dir, f"example-{example}{suffix}")
            self.run(f'"{binary}"')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["ruckig"]
        self.cpp_info.set_property("cmake_file_name", "ruckig")
        self.cpp_info.set_property("cmake_target_name", "ruckig::ruckig")
        self.cpp_info.set_property("pkg_config_name", "ruckig")
        if self.settings.os == "Windows":
            self.cpp_info.defines.append("_USE_MATH_DEFINES")
        elif self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.defines.append("_GNU_SOURCE")
