#!/usr/bin/env python3
"""Conan recipe — args 6.6.0 (CMake header-only library).

args 是 Taywee 出品的单文件 header-only C++ 命令行参数解析库。
header-only（CMake INTERFACE library），无任何依赖，消费方只需 args.hxx。
"""
from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ArgsConan(ConanFile):
    name = "args"
    version = "6.6.0"
    description = "A single-header, header-only C++ argument parser library (Taywee/args)"
    license = "MIT"
    homepage = "https://github.com/Taywee/args"
    url = ""  # CI fills this
    topics = ("args", "argparse", "header-only", "cxx11", "cpp")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["ARGS_BUILD_EXAMPLE"] = False
        tc.variables["ARGS_BUILD_UNITTESTS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "args")
        self.cpp_info.set_property("cmake_target_name", "taywee::args")
        self.cpp_info.libs = []