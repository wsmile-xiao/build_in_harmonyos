#!/usr/bin/env python3
"""Conan recipe — bioparser 3.0.15（header-only C++ 生物信息学解析库）.

bioparser 是 header-only 模板库（CMake INTERFACE 目标），公开头文件
include/bioparser/*.hpp 依赖 zlib（gz 压缩 FASTA/Q 解析）。
配方安装头文件 + CMake 包配置文件，无编译产物。

R32: 无 settings.os 分支需要——OHOS 适配版 conan 自动映射
os=OHOS → CMAKE_SYSTEM_NAME=HarmonyOS。
"""
from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches


class BioparserConan(ConanFile):
    name = "bioparser"
    version = "3.0.15"
    description = "bioparser - a c++ header only parsing library for several formats in bioinformatics (FASTA/Q, MHAP/PAF/SAM), with support for zlib compressed files"
    license = "MIT"
    homepage = "https://github.com/rvaser/bioparser"
    url = "https://github.com/rvaser/bioparser"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib 为唯一运行期依赖（gz 压缩文件解析）
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 仅安装头文件与 CMake 配置，不构建测试
        tc.variables["bioparser_install"] = "ON"
        tc.variables["bioparser_build_tests"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
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
        # header-only：无库文件可链接，公开头文件 + CMake 配置随包安装
        self.cpp_info.set_property("cmake_file_name", "bioparser")
        self.cpp_info.set_property("cmake_target_name", "bioparser::bioparser")
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # INTERFACE 目标已把 zlib 作为公开链接需求，消费者经 CMakeDeps 自动获得
