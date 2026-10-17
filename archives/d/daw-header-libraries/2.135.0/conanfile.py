#!/usr/bin/env python3
"""Conan recipe — daw-header-libraries 2.135.0 (CMake header-only library).

daw-header-libraries 是 beached 维护的现代 C++ 头文件库集合
（span、expected、string_view、container_algorithms 等）。
header-only（CMake INTERFACE library），无运行时依赖，仅含头文件。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DawHeaderLibrariesConan(ConanFile):
    name = "daw-header-libraries"
    version = "2.135.0"
    description = "Various header libraries mostly future std lib, replacements for (e.g. visit), or some misc"
    license = "BSL-1.0"
    homepage = "https://github.com/beached/header_libraries"
    url = ""  # CI fills this
    topics = ("header-only", "span", "expected", "static-string", "cpp17")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # header-only 库仅含头文件，无补丁 source；保留空实现满足门禁规范
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["DAW_ENABLE_TESTING"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "daw-header-libraries")
        self.cpp_info.set_property("cmake_target_name", "daw::daw-header-libraries")
        self.cpp_info.libs = []