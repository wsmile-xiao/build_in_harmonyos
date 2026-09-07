#!/usr/bin/env python3
"""Conan recipe — oystr 0.2.0 (CMake)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class OystrConan(ConanFile):
    name = "oystr"
    version = "0.2.0"
    description = "Recursively search directories for a substring"
    license = "MIT"
    package_type = "application"
    homepage = "https://github.com/p-ranav/oystr"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*", "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("argparse/3.2")
        self.requires("fmt/12.2.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # The installed CMake has no OHOS platform module; the OHOS
            # clang/sysroot is Linux-compatible for this ordinary C++ target.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["oystr_DEVELOPER_MODE"] = "ON"
        tc.cache_variables["BUILD_TESTING"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"], build_tool_args=["-j1"])
        cmake.test(cli_args=["--parallel", "1"], build_tool_args=["-j1"])

    def package(self):
        copy(self, "oy", src=os.path.join(self.build_folder, ""), dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.define_path("OYSTR", os.path.join(self.package_folder, "bin", "oy"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
