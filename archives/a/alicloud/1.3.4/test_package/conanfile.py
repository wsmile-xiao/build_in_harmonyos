#!/usr/bin/env python3
"""Conan test_package for alicloud (MNS C++ SDK) — compile+link a minimal consumer."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AlicloudTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明 alicloud 的传递依赖(curl/openssl)使 CMakeDeps 生成完整
        # include 配置 —— 否则 CURL_INCLUDE_DIRS 为空,test 编译找不到 curl/curl.h
        self.requires("curl/8.15.0")
        self.requires("openssl/3.5.6.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d: test() 必须含 self.run() 调用（不能是 stub）
        # CMake 构建产物在 build 目录,不在 PATH 中 → 用绝对路径运行
        import os
        _bin = os.path.join(self.build_folder, "test_alicloud")
        if not os.path.exists(_bin):
            raise ConanException("test_alicloud binary not found at {}".format(_bin))
        self.run(_bin, env="conanrun")
