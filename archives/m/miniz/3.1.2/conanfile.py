#!/usr/bin/env python3
"""Conan recipe — miniz 3.1.2.

miniz is a single-file ZIP/DEFLATE/inflate library providing a
zlib-compatible API (mz_compress/mz_uncompress/mz_compressBound) plus a
full ZIP archive reader/writer.

Build system: upstream native CMake. The non-amalgamation build path
compiles miniz.c / miniz_zip.c / miniz_tinfl.c / miniz_tdef.c and already
sets VERSION/SOVERSION on the shared library, so DT_SONAME is produced
without a patch.

miniz is a system-name-collision library (zlib provides a libz.so on the
host); the recipe forces BUILD_SHARED_LIBS=OFF per R26 and ships only the
static libminiz.a + headers + pkg-config + cmake package config.
"""
from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MinizConan(ConanFile):
    name = "miniz"
    version = "3.1.2"
    description = (
        "Single-file ZIP/DEFLATE/inflate library with a zlib-compatible "
        "API and a full ZIP archive reader/writer"
    )
    license = "MIT"
    homepage = "https://github.com/richgel999/miniz"
    url = "https://github.com/richgel999/miniz"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        # 纯 C 库，无外部依赖（仅 libc；miniz_zip.c 在非 Windows 路径使用
        # ftello/fseeko/stat，标准 libc 提供）
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # miniz 与宿主 zlib (libz.so) 同名：强制静态库，避免系统同名库冲突 (R26)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # 关闭 examples / fuzzers / 上游开发测试（实际 3.1.2 CMake option 名）
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_FUZZERS"] = "OFF"
        tc.variables["BUILD_TESTS"] = "OFF"
        # 用上游原生多文件构建（非 amalgamation / 非 header-only）
        tc.variables["AMALGAMATE_SOURCES"] = "OFF"
        tc.variables["BUILD_HEADER_ONLY"] = "OFF"
        # 保留 stdio（test_package 使用 zlib-compat 内存 API，但 zip 读写依赖 stdio）
        tc.variables["BUILD_NO_STDIO"] = "OFF"
        # 安装目标 + cmake package config + pkg-config
        tc.variables["INSTALL_PROJECT"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 上游安装头文件到 include/miniz/（INSTALL_INCLUDEDIR/miniz），
        # 允许 <miniz.h> 与 <miniz/miniz.h> 两种包含方式
        self.cpp_info.includedirs = ["include/miniz"]
        self.cpp_info.libs = ["miniz"]
        # 静态库消费方需定义 MINIZ_STATIC_DEFINE（上游 generate_export_header 约定）
        self.cpp_info.defines = ["MINIZ_STATIC_DEFINE"]
