#!/usr/bin/env python3
"""Conan test_package — libeis 1.6.0 消费者测试（L1 official test）。

CI 在 conan create 时自动执行。C 消费者程序真实链接 libeis.so 并调用
公共 API：上下文生命周期、日志回调、UNIX socket 后端（bind/listen/accept/
握手前事件门/退出清理）与私有 fd 后端，全部由返回值与 errno 决定断言。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
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
        # OHOS 上 /tmp 只读（E002）：给消费者测试指定可写短路径目录
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp"
        )
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("LIBEIS_TEST_DIR", tmpdir)
        env.define("TMPDIR", tmpdir)
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libeis")
        with env.vars(self, scope="run").apply():
            # 断言失败 ⇒ 非零退出 ⇒ conan create 失败（真实门禁）
            self.run(f'"{exe}"', env="conanrun")
