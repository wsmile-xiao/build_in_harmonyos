#!/usr/bin/env python3
"""Conan recipe for libftp 1.5.0 (FTP/FTPS client library, CMake).

Upstream: https://github.com/deniskovalchuk/libftp
- CMake target: ftp -> libftp.a
- Requires Boost >= 1.88.0 (find_package(Boost REQUIRED CONFIG) -> Boost::boost)
- Requires OpenSSL (find_package(OpenSSL REQUIRED) -> OpenSSL::SSL)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class LibftpConan(ConanFile):
    name = "libftp"
    version = "1.5.0"
    description = "libftp 1.5.0 — FTP/FTPS client library (C++17)"
    license = "MIT"
    homepage = "https://github.com/deniskovalchuk/libftp"
    url = "https://github.com/deniskovalchuk/libftp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.90.0", transitive_headers=True)
        # openssl 头文件经上游公共头（boost/asio/ssl → openssl）暴露给消费者，
        # 必须传递头文件可见性，否则下游 test_package 拿不到 openssl include。
        self.requires("openssl/3.5.6.1.1", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CMakeDeps 生成 Boost/OpenSSL 的 CMake config（上游 find_package CONFIG 模式）
        deps = CMakeDeps(self)
        # openssl/3.5.6.1.1 是 flat 包（libs ssl+crypto，无 OpenSSL::SSL 目标），
        # CMakeDeps 默认生成 openssl::openssl；上游 CMakeLists 用 find_package(OpenSSL)
        # + OpenSSL::SSL，故把目标名直接映射为 OpenSSL::SSL（config 模式优先于
        # 内置 FindOpenSSL 模块，OPENSSL_ROOT_DIR 缓存变量不会生效）。
        deps.set_property("openssl", "cmake_target_name", "OpenSSL::SSL")
        deps.generate()
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 上游测试依赖 FetchContent googletest（构建期网络）+ Boost::process，
        # CI 环境不可用；上游测试由本地 upstream_tests 门禁单独处理。
        tc.variables["LIBFTP_BUILD_TEST"] = "OFF"
        tc.variables["LIBFTP_BUILD_EXAMPLE"] = "OFF"
        tc.variables["LIBFTP_BUILD_CMDLINE_CLIENT"] = "OFF"
        if str(self.settings.os) == "OHOS":
            # E092: CMake 无内置 OHOS platform module，沿用 Linux 平台模型 +
            # aarch64 处理器描述（同 burst/coin3 既有 OHOS 配方做法）
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
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
        # CMake 目标为 `ftp`（产物 libftp.a / libftp.so），链接名不带 lib 前缀
        self.cpp_info.libs = ["ftp"]
        # 上游公共头文件依赖 Boost（boost/asio/ssl）与 OpenSSL 头文件，
        # 消费者（test_package）编译时必须能拿到二者的 include 路径。
        self.cpp_info.requires = ["boost::boost", "openssl::openssl"]
        self.cpp_info.set_property("cmake_file_name", "libftp")
        self.cpp_info.set_property("cmake_target_name", "libftp::libftp")
