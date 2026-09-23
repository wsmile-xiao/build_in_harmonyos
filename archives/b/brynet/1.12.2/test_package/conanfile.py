#!/usr/bin/env python3
"""Test package for brynet 1.12.2 (header-only C++11 TCP network library).

消费者验证 + HarmonyOS 专项测试：
- 通过 find_package(brynet) 链接打包后的头文件
- 真实调用 brynet API：TcpService + ListenerBuilder 起 127.0.0.1 回环 echo
  服务，ConnectionBuilder 同步连接、发送并回读数据，验证 OHOS 网络栈与
  brynet 事件循环可正常工作（非空壳测试，R34）。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BrynetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_brynet_ohos"), env="conanrun")
