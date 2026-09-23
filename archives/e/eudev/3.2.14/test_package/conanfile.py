#!/usr/bin/env python3
"""Conan test_package for eudev 3.2.14.

eudev 同时提供库（libudev）与工具（udevadm / udevd），测试方式为**真实执行**：
  - udevadm --version   断言 udev 协议版本 251
    （注意：251 是 udev 协议版本，对应 systemd 251，**不是**包版本 3.2.14）
  - libudev.so 存在（真正被消费者链接的产物）

实际断言由 test_eudev.sh 承担（L0c 真实测试源文件），共 4 项。
"""
import os

from conan import ConanFile


class EudevTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_eudev.sh")
        # env="conanrun"：udevadm 为动态链接可执行文件，运行时需 LD_LIBRARY_PATH
        # 含本包及依赖的 lib 目录，否则报符号缺失。
        self.run(f"sh '{script}' '{pkg}'", env="conanrun")
