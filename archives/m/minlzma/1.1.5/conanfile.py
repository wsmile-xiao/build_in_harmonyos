#!/usr/bin/env python3
"""Conan recipe — minlzma 1.1.5 (minimal LZMA2/XZ decompression C library + minlzdec CLI).

minlzma 是 Alex Ionescu 的最小化、跨平台、纯 C11 LZMA2/XZ 解压库
（minlzlib，静态库），并提供命令行工具 minlzdec。公共 API 为 minlzma.h
中的 XzDecode()/XzChecksumError()。

上游 CMake 工程未提供 install() 规则，本配方在 package() 中手动 copy
头文件、静态库与 CLI 可执行文件（对齐仓库内无 install 规则的 CMake 库先例）。
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building
import os


class MinlzmaConan(ConanFile):
    name = "minlzma"
    version = "1.1.5"
    description = "minlzma - Minimal LZMA2/XZ decompression C library (C11) with minlzdec CLI"
    license = "MIT"
    homepage = "https://github.com/ionescu007/minlzma"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

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
        # R26: 非系统同名库默认由 Conan 管理依赖链；minlzma 无系统同名冲突，
        # 按选项切换静态/共享。上游默认同时产出 minlzlib(static)+minlz(shared)，
        # 静态模式下关掉共享目标避免重复链接。
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # 上游无 install() 规则：手动收集产物。
        # 上游 CMake 将库目标（minlzlib 静态 / minlz 共享）构建在
        # build 目录的 minlzlib/ 子目录，minlzdec 在 minlzdec/ 子目录；
        # 必须显式指定源子目录并 keep_path=False，否则 CMakeDeps
        # 在 lib/ 根目录找不到库（前次 G2 失败根因）。
        inc_dir = os.path.join(self.package_folder, "include")
        lib_dir = os.path.join(self.package_folder, "lib")
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "minlzma.h", src=self.source_folder, dst=inc_dir)
        copy(self, "*.a", src=os.path.join(self.build_folder, "minlzlib"),
             dst=lib_dir, keep_path=False)
        copy(self, "*.so*", src=os.path.join(self.build_folder, "minlzlib"),
             dst=lib_dir, keep_path=False)
        copy(self, "minlzdec", src=os.path.join(self.build_folder, "minlzdec"),
             dst=bin_dir, keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        if self.options.shared:
            self.cpp_info.libs = ["minlz"]
        else:
            self.cpp_info.libs = ["minlzlib"]
        self.cpp_info.bindirs = ["bin"]
