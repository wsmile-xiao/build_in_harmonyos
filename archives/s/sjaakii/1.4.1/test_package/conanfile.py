#!/usr/bin/env python3
"""test_package — sjaakii 1.4.1（上游测试面: `test movegen` 7 变体 perft 参考计数）。

L1 消费者验证：conan create 自动执行。上游无 ctest/make check，测试面是引擎
内置的 `test movegen` 命令（src/xboard.cc: 7 个变体的 perft 参考位点数组）。
产物为静态链接（conan readline/ncurses 均 .a），无 runenv 依赖，直接绝对路径驱动。
"""
import os
import sys

from conan import ConanFile


class SjaakiiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.conf.get("tools.build:skip_test", check_type=bool):
            return
        bin_dir = os.path.join(self.dependencies["sjaakii"].package_folder, "bin")
        # sys.executable 绝对路径（OHOS python 子进程裸命令名 ENOENT，device-facts §一.14）
        self.run(f'"{sys.executable}" test_sjaakii.py "{os.path.abspath(bin_dir)}"')
