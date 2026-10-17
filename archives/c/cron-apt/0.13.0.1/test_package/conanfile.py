#!/usr/bin/env python3
"""Conan test_package for cron-apt 0.13.0.1.

cron-apt 是纯 shell 脚本包 —— 测试方式为**真实执行**：
  ① bin/cron-apt 存在 + 可执行 + sh -n 语法
  ② share/cron-apt/functions 已打包
  ③ 运行时执行 cron-apt --help 并断言输出 USAGE（R34）

实际逻辑由 test_cron_apt.sh 承担（真实测试源文件，L0c 要求）。
"""
import os

from conan import ConanFile


class CronAptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_cron_apt.sh")
        self.run(f"sh '{script}' '{pkg}'")
