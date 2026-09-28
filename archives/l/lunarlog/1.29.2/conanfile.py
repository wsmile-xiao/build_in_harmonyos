#!/usr/bin/env python3
"""Conan recipe for lunarlog 1.29.2 — header-only C++11 structured logging.

LunarLog is a header-only library (CMake INTERFACE target). The recipe
exports only headers + CMake config, matching the upstream conanfile.py
layout (package_type=header-library, no compiled artifacts).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
import os


class LunarlogConan(ConanFile):
    name = "lunarlog"
    version = "1.29.2"
    description = "Header-only C++11 structured logging with message templates"
    license = "MIT"
    homepage = "https://github.com/LunarECL/LunarLog"
    url = "https://github.com/LunarECL/LunarLog"
    topics = ("logging", "structured-logging", "header-only", "cpp11", "message-templates")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["LUNARLOG_BUILD_TESTS"] = "OFF"
        tc.variables["LUNARLOG_BUILD_EXAMPLES"] = "OFF"
        tc.variables["LUNARLOG_BUILD_BENCHMARKS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.hpp", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        # CMake package config so downstream can find_package(LunarLog)
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "LunarLog")
        self.cpp_info.set_property("cmake_target_name", "LunarLog::LunarLog")
        if self.settings.os in ["Linux", "FreeBSD", "OHOS"]:
            self.cpp_info.system_libs.append("pthread")

    def package_id(self):
        self.info.clear()
