#!/usr/bin/env python3
"""Conan test_package for nutcracker — daemon 冒烟测试.

R34/PF3: test() 必须 self.run 实际执行被测包二进制，禁止空壳。
执行 test_nutcracker.sh：
  1. nutcracker -V 版本断言（纯 IO）
  2. nutcracker -t 最小 YAML 配置校验
  3. daemon 起进程 + 端口探测 + 正常 shutdown
  4. 本地 nc 假后端做一次 Redis 转发验证（有 nc 时）
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class NutcrackerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies["nutcracker"]
        nutcracker = os.path.join(dep.package_folder, "sbin", "nutcracker")
        script = os.path.join(self.source_folder, "test_nutcracker.sh")
        self.run(f'bash "{script}" "{nutcracker}"', env="conanrun")