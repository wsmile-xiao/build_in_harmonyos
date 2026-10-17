#!/usr/bin/env python3
"""Test package for uctodata 0.11.

两级验证：① `consumer_ucto.py` —— 完整消费者用例（端到端：pkg-config 契约 →
`tokconfig-nld` → `%include` 的数据文件）；② `test_data.py` —— 19~20 条适配自检断言。

Data-only package: the assertions below are the only executable check that the
Conan package carries a *usable* payload rather than just a non-empty file list.
The decisive one is the pkg-config contract, because that is literally how ucto
locates these files (ucto/configure.ac: `pkg-config --variable=prefix uctodata`
-> $prefix/share/ucto).

Delegates to test_data.py (standalone test source file).
"""
import os
import sys

from conan import ConanFile


class UctodataTestConan(ConanFile):
    # Data-only package: no compilation, no settings needed.

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["uctodata"]
        package_folder = dep.package_folder

        # ① 完整消费者用例（平台 rule12）：走 ucto 的真实启动路径把数据消费一遍
        #    （pkg-config 契约 → tokconfig-nld → %include 的数据文件逐条解析）
        consumer = os.path.join(self.source_folder, "consumer_ucto.py")
        self.run(f"{sys.executable} {consumer} {package_folder}")

        # ② 适配自检（M=19~20，非上游用例；上游 N=0）
        test_script = os.path.join(self.source_folder, "test_data.py")
        self.run(f"{sys.executable} {test_script} {package_folder}")
