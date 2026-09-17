#!/usr/bin/env python3
"""Conan test_package — daps 3.3.2-cleaned1 实质测试

daps 是 bash 脚本工具套件（无 C/C++ 库产物），L1 测试执行独立测试源
test.sh（4 断言）：
1. daps --version 输出版本号 3.3.2
2. daps --help 输出使用帮助
3. daps --commands 列出支持子命令
4. daps-check-deps 检查运行时依赖探测功能
"""
import os

from conan import ConanFile


class DapsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        daps_bin = os.path.join(
            self.dependencies["daps"].package_folder, "bin", "daps")
        daps_check = os.path.join(
            self.dependencies["daps"].package_folder, "bin", "daps-check-deps")
        bash = "/data/service/hnp/bin/bash"
        self.run(
            f'DAPS_BIN="{daps_bin}" DAPS_CHECK="{daps_check}" '
            f'"{bash}" test.sh',
            env="conanrun")