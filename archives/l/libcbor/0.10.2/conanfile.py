#!/usr/bin/env python3
"""Conan recipe — libcbor 0.10.2 (CMake project).

libcbor is a pure C library for parsing and generating CBOR (RFC 7049).
It uses CMake and produces a static library libcbor.a plus headers.
No external runtime dependencies (test dependency cmocka is build-only).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibcborConan(ConanFile):
    name = "libcbor"
    version = "0.10.2"
    description = "C library for parsing and generating CBOR (Concise Binary Object Representation)"
    license = "MIT"
    homepage = "https://github.com/PJK/libcbor"
    url = "https://github.com/PJK/libcbor"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "pretty_printer": [True, False]}
    default_options = {"shared": False, "pretty_printer": True}

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
        # R26: static by default
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CBOR_PRETTY_PRINTER"] = "ON" if self.options.pretty_printer else "OFF"
        # 上游 CMakeLists.txt 声明 cmake_minimum_required(3.0)，而本环境 CMake 4.x
        # 已移除对 <3.5 的兼容，需显式声明最低策略版本（否则 conan create 配置失败）
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM 必须在 cmake_minimum_required 解析前以
        # -D 命令行参数注入（CMake 4.x 已移除对 <3.5 的兼容，上游声明 3.0）
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["cbor"]
