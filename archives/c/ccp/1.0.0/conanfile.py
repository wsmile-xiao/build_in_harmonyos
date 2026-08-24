#!/usr/bin/env python3
"""Conan recipe — ccp 1.0.0 (libccp, CCP-compatible datapath library).

Build system: CMake (upstream also ships a Makefile; CMake provides install
rules for lib + headers + cmake package config, preferred for Conan).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CcpConan(ConanFile):
    name = "ccp"
    version = "1.0.0"
    description = "libccp — a library for implementing CCP-compatible datapaths"
    license = "ISC"
    homepage = "https://github.com/ccp-project/libccp"
    url = "https://github.com/ccp-project/libccp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 纯 C 库，无外部依赖（仅 libc）
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 CMakeLists 同时构建 ccp(SHARED) 与 ccp_static(STATIC)；
        # 非系统同名库，按 shared 选项控制默认行为（R26 不适用）
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # HarmonyOS 未映射到 CMake 已知平台，SONAME 相关变量未定义，
        # 共享库会缺 DT_SONAME（W3 CI L5 soname gate 失败）。
        # 参照 attica5 已验证模式：注入 SONAME 标志但跳过版本化符号链接
        # （HMDFS 对符号链接敏感），保证 DT_SONAME 存在且可重定位。
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
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
        # 上游安装头文件到 include/ccp/（ccp.h/types.h/ccp_error.h）
        self.cpp_info.includedirs = ["include/ccp"]
        self.cpp_info.libs = ["ccp"]
