#!/usr/bin/env python3
"""Conan recipe — cpp-httplib 0.18.0 (CMake header-only HTTP/HTTPS library).

cpp-httplib 是一个 C++ 单头文件 HTTP/HTTPS 客户端/服务端库（header-only，
默认 HTTPLIB_COMPILE=OFF，仅安装 httplib.h）。可选依赖 OpenSSL/Zlib/Brotli，
header-only 模式下为 INTERFACE library，无二进制编译。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class CppHttplibConan(ConanFile):
    name = "cpp-httplib"
    version = "0.18.0"
    description = "A C++ header-only HTTP/HTTPS server and client library"
    license = "MIT"
    homepage = "https://github.com/yhirose/cpp-httplib"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: 平台判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "cpp-httplib 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only 库，所有 settings 组合产出相同的包内容
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.cache_variables["HTTPLIB_INSTALL"] = True
        tc.cache_variables["HTTPLIB_TEST"] = False
        tc.cache_variables["HTTPLIB_COMPILE"] = False
        # header-only 模式仅安装头文件；禁用 optional 依赖查找，避免网络/工具链耦合
        tc.cache_variables["HTTPLIB_USE_OPENSSL_IF_AVAILABLE"] = False
        tc.cache_variables["HTTPLIB_USE_ZLIB_IF_AVAILABLE"] = False
        tc.cache_variables["HTTPLIB_USE_BROTLI_IF_AVAILABLE"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 上游 find_package(httplib) -> httplib::httplib
        self.cpp_info.set_property("cmake_file_name", "httplib")
        self.cpp_info.set_property("cmake_target_name", "httplib::httplib")
        self.cpp_info.libs = []
