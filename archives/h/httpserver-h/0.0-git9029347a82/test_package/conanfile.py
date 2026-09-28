#!/usr/bin/env python3
"""Conan test_package — 验证 httpserver.h 头文件可被真实使用。

消费者测试：启动一个 HTTP 服务器（epoll 后端），客户端 socket 发送 GET 请求，
轮询驱动服务器事件循环，验证 handler 被调用且返回 200 OK + 响应体。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class HttpserverHTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.build_folder, "test_httpserver_h")
        self.run(bin_path, env="conanrun")
        hos_path = os.path.join(self.build_folder, "test_hos")
        self.run(hos_path, env="conanrun")