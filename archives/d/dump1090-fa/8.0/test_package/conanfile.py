#!/usr/bin/env python3
"""Conan test_package — dump1090-fa 8.0.

消费者测试：真实执行已安装的 dump1090 二进制（R34），验证 --version/--help
可用并输出正确版本与用法，再以自定义 `--help` 参数确认退出码。
"""
import os

from conan import ConanFile


class Dump1090FaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["dump1090-fa"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_dump1090.sh")
        # OHOS 下 /system/bin/sh 无法执行 ELF，用 bash 包装
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" "{script}" "{bin_dir}"')
