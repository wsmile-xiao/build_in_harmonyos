#!/usr/bin/env python3
"""Conan test_package — consolation 0.0.10 L0c real-execution test.

consolation 同时是库消费者与可执行守护进程，测试方式为**真实执行**
（同 eudev 3.2.14 的 L0c 模式）：
  - 定位 sbin/consolation
  - `consolation --version` 成功退出
  - `consolation --help` 成功退出并输出用法

实际断言由 test_consolation.sh 承担，共 3 项。
"""
import os

from conan import ConanFile


class ConsolationTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_consolation.sh")
        # env="conanrun"：consolation 动态链接 libinput/libudev/libevdev，
        # 运行时需 LD_LIBRARY_PATH 含依赖包的 lib 目录。
        self.run(f"sh '{script}' '{pkg}'", env="conanrun")
