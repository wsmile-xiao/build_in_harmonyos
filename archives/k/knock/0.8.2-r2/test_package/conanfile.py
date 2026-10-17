#!/usr/bin/env python3
"""Conan test_package for knock 0.8.2-r2 — binary tool smoke test.

knock 是 application（无可链接库），测试通过执行 knock 二进制并断言其输出，
满足 R34（test 必须实质依赖被测包）。

交叉编译时（CI 构建机为不同架构）can_run 返回 False，跳过执行——
此时仅验证二进制存在；本机架构匹配时执行 --version/--help 断言。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class KnockTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _knock_bin(self):
        bin_path = os.path.join(self.dependencies["knock"].package_folder, "bin", "knock")
        if not os.path.exists(bin_path):
            for root, dirs, files in os.walk(self.dependencies["knock"].package_folder):
                if "knock" in files:
                    bin_path = os.path.join(root, "knock")
                    break
        return bin_path

    def test(self):
        bin_path = self._knock_bin()
        # R34: 实质依赖被测包——执行 knock 二进制并断言输出
        # can_run 守卫：交叉编译架构不匹配时跳过执行（CI 构建机与目标架构不同）
        if not can_run(self):
            self.output.info("Cross-building: skip binary execution, only verify existence")
            if not os.path.exists(bin_path):
                raise AssertionError(f"knock binary not found at {bin_path}")
            return
        # 本机可执行：调用 test_knock.sh 执行 --version + --help 断言
        script = os.path.join(os.path.dirname(__file__), "test_knock.sh")
        self.run(f'bash "{script}" "{bin_path}"', env="conanrun")
