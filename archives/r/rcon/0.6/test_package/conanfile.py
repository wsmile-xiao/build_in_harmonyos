#!/usr/bin/env python3
"""Conan test_package — rcon 0.6 消费者测试（L1 + 鸿蒙特有测试）。

rcon 是纯可执行文件包（R38 application）。测试程序编译自身，运行两层用例：
1) 冒烟：调用被测二进制 `rcon --help`，断言退出码与用法输出（R34/PF3）；
2) 端到端消费者用例（鸿蒙特有测试，新增）：本地起最小 RCON 服务器
   （127.0.0.1 真实 TCP socket），驱动 `rcon` 二进制完成真实 auth+command
   往返，校验服务器收到的报文与客户端输出的响应体，端到端跑通功能/流程。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class RconTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # 纯可执行包：无需 CMakeDeps（无可链接目标）
    generators = "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 真实执行消费者测试二进制（内部调用 rcon --help 并断言行为）
        exe = os.path.join(self.cpp.build.bindir, "test_rcon")
        if can_run(self):
            self.run(exe, env="conanrun")
        else:
            self.output.info("cross-compiling: test_package binary compiled but not executed")
