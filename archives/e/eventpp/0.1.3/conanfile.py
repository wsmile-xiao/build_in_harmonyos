#!/usr/bin/env python3
"""Conan recipe — eventpp 0.1.3 (CMake header-only library).

eventpp is a C++ event library for callbacks, event dispatcher, and event queue.
It is header-only, requires C++11, and has zero external dependencies.
Uses CMake with INTERFACE library target.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class EventppConan(ConanFile):
    name = "eventpp"
    version = "0.1.3"
    description = "C++ event library for callbacks, event dispatcher, and event queue"
    license = "Apache-2.0"
    homepage = "https://github.com/wqking/eventpp"
    url = "https://cnb.cool/OpenHarmonyPCDeveloper/build_in_harmonyos/-/tree/main/archives/e/eventpp/0.1.3"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only 库：package_id 不依赖编译器/构建类型/架构
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.cache_variables["EVENTPP_INSTALL"] = "ON"
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
        self.cpp_info.set_property("cmake_file_name", "eventpp")
        self.cpp_info.set_property("cmake_target_name", "eventpp::eventpp")
        self.cpp_info.libs = []
