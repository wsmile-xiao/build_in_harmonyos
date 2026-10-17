#!/usr/bin/env python3
"""Conan recipe — openddl-parser 0.5.2 (CMake, static library).

openddl-parser 是一个 C++ OpenDDL 解析器库（Assimp 的 OpenDDL 解析依赖）。
上游构建系统为 CMake（本项目 README 上游官方 tag v0.5.2 即 CMakeLists.txt
驱动），产物为静态库 libopenddlparser.a + 公开头文件 include/openddlparser/。
本配方采用官方 CMake 模板：configure -> build -> install，无第三方依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OpenddlParserConan(ConanFile):
    name = "openddl-parser"
    version = "0.5.2"
    description = "OpenDDL parser library (used by Assimp for OpenDDL/OGEX parsing)"
    license = "MIT"
    homepage = "https://github.com/kimkulling/openddl-parser"
    url = "https://github.com/kimkulling/openddl-parser"

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 测试与 demo 由上游默认构建；配方安装目标仅含库与头文件（无 bin 产物）
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
        self.cpp_info.libs = ["openddlparser"]
