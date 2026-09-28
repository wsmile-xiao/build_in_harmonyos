#!/usr/bin/env python3
"""Conan test_package for sash 3.8.

R34：测试必须实质执行被测包 —— 这里真跑 sash 二进制，并且有一条断言
专门穿过 zlib 代码路径（-gzip / -gunzip 往返），证明被测包与本包唯一
外部依赖之间的链接与运行都真实可用，不是打印字符串的空壳。

断言设计原则（本包大量内建命令是特权操作，OHOS PC 沙箱非 root）：
所有断言都选**不依赖特权**的路径 —— 参数解析 / usage() / 内建命令表分派 /
zlib 压缩往返，全部在普通用户 + 可写临时目录下即可完成。
"""
import os

from conan import ConanFile


class SashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(
            self.dependencies["sash"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_sash.sh")
        self.run(f'sh "{script}" "{bin_dir}"')
