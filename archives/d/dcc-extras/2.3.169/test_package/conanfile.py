#!/usr/bin/env python3
"""Conan test_package — dcc-extras 2.3.169（L1 消费者测试）。

两部分：
  1) C 消费者测试（CMake 目标 test_dcc）：链接包内 libdcc 并调用其 API，
     同时断言 OHOS 专有的 u_char/u_int32_t/caddr_t 可用（本包补丁生效点）。
  2) test_dcc-extras.sh（13 例）：包布局契约 + 上游二进制真实执行 +
     OHOS 平台专有用例。

上游无自动化测试套件，清点证据见 test_package/MANIFEST.yml 与
reports/test-report.md §1（R51 三步法）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DccExtrasTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        # 1) C 消费者测试（真实链接 libdcc 并调用 API）
        exe = os.path.join(self.cpp.build.bindirs[0], "test_dcc")
        self.run(f'"{exe}"', env="conanrun")

        # 2) 包布局 / 上游二进制执行 / OHOS 平台用例套件
        pkg = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(os.path.dirname(__file__), "test_dcc-extras.sh")
        self.run(f'bash "{script}" "{pkg}"', env="conanrun")
