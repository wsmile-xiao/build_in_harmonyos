#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Miniscript, miniscript, 1.6.2, miniscript 1.6.2, MIT, 
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

import os


class MiniscriptConan(ConanFile):
    name = "miniscript"
    version = "1.6.2"
    description = "MiniScript — a tiny, embeddable scripting language (C++ implementation)"
    license = "MIT"
    homepage = "https://github.com/JoeStrout/miniscript"
    url = "https://github.com/JoeStrout/miniscript"

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
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["MINISCRIPT_BUILD_TESTING"] = "ON"
        tc.variables["MINISCRIPT_BUILD_CSHARP"] = "OFF"
        # OHOS/arm64 默认 unsigned char，上游单元测试与 UTF-8 字节 API
        # 依赖 signed char 语义（Assert(s.atB(0) == -26)），与 x86 Linux 对齐
        tc.extra_cflags = ["-fsigned-char"]
        tc.extra_cxxflags = ["-fsigned-char"]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游 CMake 仅 install(TARGETS ...) 不安装头文件，这里按上游目录结构
        # 补充安装公开头文件（MiniScript/*.h），保持 #include <MiniScript/...> 可用
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "MiniScript-cpp", "src", "MiniScript"),
             dst=os.path.join(self.package_folder, "include", "MiniScript"))

    def package_info(self):
        # 上游 install(TARGETS miniscript-cpp minicmd) 同时安装库与 CLI（bin/miniscript）
        self.cpp_info.libs = ["miniscript-cpp"]
        self.cpp_info.bindirs = ["bin"]
