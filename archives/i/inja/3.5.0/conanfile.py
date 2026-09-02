#!/usr/bin/env python3
"""Conan recipe for inja 3.5.0, a header-only C++17 templating library."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class InjaConan(ConanFile):
    name = "inja"
    version = "3.5.0"
    description = "Modern C++ template engine with an embedded nlohmann::json fallback."
    license = "MIT"
    homepage = "https://github.com/pantor/inja"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("template", "json", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["INJA_BUILD_TESTS"] = "ON"
        tc.variables["INJA_USE_EMBEDDED_JSON"] = "ON"
        tc.variables["INJA_INSTALL"] = "ON"
        tc.variables["INJA_INSTALL_SINGLE_HEADER"] = "OFF"
        tc.variables["INJA_EXPORT"] = "OFF"
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_nlohmann_json"] = "TRUE"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--target", "inja_test", "single_inja_test"])
        cmake.test()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "inja")
        self.cpp_info.set_property("cmake_target_name", "pantor::inja")
