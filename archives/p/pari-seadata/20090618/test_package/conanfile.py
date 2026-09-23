#!/usr/bin/env python3
"""Conan test_package — pari-seadata (纯数据包, R34 内容级校验).

pari-seadata 无库、无二进制、无上游测试套件（见 test_package/MANIFEST.yml）。
唯一的可验证交付物是打包进 <pkg>/res/pari/seadata/ 的模多项式数据。

本测试脚本对**被测包的真实内容**做校验（非打印空壳）：
  1. seadata 目录存在，且含 51 个 sea<p> 数据文件 + README；
  2. 每个 sea* 文件为 GP 文本格式（首字符 '['）且非空；
  3. 全部 sea* 拼接 sha256 == 上游基线指纹
     c055c577d25f7f0e1a9cf90d699df846b4ecde5b7cb64debae1dc2f50f1aa738
     ——若包丢了/错任何一个字节都会红。
若数据缺失或被篡改，脚本返回非 0，conan create 的 test 阶段即失败。
"""
import os

from conan import ConanFile


class PariSeadataTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["pari-seadata"].package_folder
        seadata = os.path.join(pkg, "res", "pari", "seadata")
        script = os.path.join(self.source_folder, "test_verify.py")
        # R34: 校验被测包真实打包内容。数据校验 host-python 无关目标架构，直接执行。
        self.run(f'python3 "{script}" "{seadata}"', env="conanrun")
