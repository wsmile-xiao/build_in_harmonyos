#!/usr/bin/env python3
"""Conan test_package — libfreefare 0.4.0 消费者视角验证 (Conan L1).

CI 通过 `conan create` 自动执行。本测试只调用不依赖物理 NFC 读卡器的纯计算/
对象生命周期 API（key 分配、AID 构造、MAD 构造、TLV 编解码、MIFARE Classic
扇区几何计算），保证无设备环境也能真实链接并运行被测库。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibfreefareTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明传递依赖，确保 test() 能拿到它们的 libdir 加到 LD_LIBRARY_PATH
        self.requires("libnfc/1.8.0")
        self.requires("openssl/3.5.6")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # CI 门禁要求 test() 显式 self.run() 执行测试程序（非仅 ctest）。
        # 运行时需要 libusb-1.0.so（libnfc 传递依赖），直接 find 它的路径。
        self.run("find /storage/Users/currentUser/.cache/conan2 -name 'libusb-1.0.so*' 2>/dev/null")
        ld_pre = "export LD_LIBRARY_PATH=$(find /storage/Users/currentUser/.cache/conan2 -name 'libusb-1.0.so*' -exec dirname {} \\; | head -1):$LD_LIBRARY_PATH && "
        # 通用消费者测试
        self.run(ld_pre + os.path.join(self.cpp.build.bindirs[0], "test_libfreefare"))
        # 鸿蒙平台专项测试（uname/__OHOS__/aarch64 小端 + 真实 API 调用）
        self.run(ld_pre + os.path.join(self.cpp.build.bindirs[0], "test_harmonyos_smoke"))
        # 上游测试用例移植（test/ 目录纯计算用例，无 Cutter 框架）
        self.run(ld_pre + os.path.join(self.cpp.build.bindirs[0], "test_upstream"))
