#!/usr/bin/env python3
"""Conan test_package for apk-tools — verifies libapk links and API works.

Calls apk_pkg_parse_name() (pure parsing API: splits "name-version" into
name/version blobs) — no apk database/network/device needed, runs at
runtime on OHOS (R34: substantive use of the tested library's API).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ApkToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libapk 公共头 apk_openssl.h include <openssl/opensslv.h>，需 openssl
        # include 路径；zlib 同理（apk.pc Requires: zlib openssl）
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R-CI L0d: test() 必须含 self.run() 直跑测试程序
        # can_run() 守卫：交叉编译时跳过运行时测试（二进制为交叉架构）
        if not can_run(self):
            self.output.info("Skipping test: cross-building build platform cannot run target binaries")
            return
        # test_apk 链接共享 libapk.so.2.14.0（lib/ 下 .a/.so 并存），运行时
        # 需 LD_LIBRARY_PATH 指向 apk-tools 包 libdir（libusbmuxd 纯静态无此问题）
        apk_lib = os.path.join(self.dependencies["apk-tools"].package_folder, "lib")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_apk")
        self.run(f'LD_LIBRARY_PATH="{apk_lib}:$LD_LIBRARY_PATH" {bin_path}', env="conanrun")
