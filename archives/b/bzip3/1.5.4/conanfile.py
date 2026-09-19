#!/usr/bin/env python3
"""Conan recipe for bzip3 1.5.4 — CMake build system.

Build approach follows archived history (1.4.0 / 1.5.3): CMake is
preferred over autotools because autotools hits HMDFS temp-dir issues
on HarmonyOS (see software-level manifest key_points).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Bzip3Conan(ConanFile):
    name = "bzip3"
    version = "1.5.4"
    description = "下一代 bzip 压缩工具，使用现代算法提供更高压缩比"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/kspalaiologos/bzip3"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # R26: system-name libs default to static; bzip3 is not a system
        # lib name, but static keeps the CLI self-contained on OHOS.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BZIP3_BUILD_APPS"] = "ON"
        tc.variables["BZIP3_ENABLE_PTHREAD"] = "ON"
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
        self.cpp_info.set_property("cmake_file_name", "bzip3")
        self.cpp_info.set_property("cmake_target_name", "bzip3::bz3")
        self.cpp_info.set_property("pkg_config_name", "bzip3")
        self.cpp_info.libs = ["bzip3"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.bindirs = ["bin"]
