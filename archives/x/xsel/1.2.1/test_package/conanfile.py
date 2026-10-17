#!/usr/bin/env python3
"""Conan test_package — xsel 1.2.1 (CLI 冒烟测试).

xsel 是命令行工具（无库可链接）：消费者测试真实执行打包的 xsel 二进制。
xsel 的 --version / --help 在 XOpenDisplay 之前就 exit(0)，
无 X server 的 headless 环境也能验证二进制可执行、版本与用法输出正确（R34）。
"""

import os

from conan import ConanFile


class XselTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 执行 ELF 不可靠，用 bash 包装
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_xsel.sh", env="conanrun")
