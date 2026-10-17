#!/usr/bin/env python3
"""Conan test_package — pari-galpol (纯数据包, R34 打包内容级校验).

pari-galpol 无库、无二进制、无上游自动化测试（上游测试入口的实证与 7337 项实跑记录见
同级 MANIFEST.yml 与版本目录的 upstream-test-cases.txt）。唯一的可验证交付物是打包进
`<pkg>/res/pari/galpol/` 的 GALPOL 数据树。

本测试对被测包**真实内容**做字节级校验（非打印空壳）：
  - 14681 个条目齐全（3657 real + 3537 complex + 3657 group + 3657 name
    + 143 nb + 29 non-wss + README），143 个阶目录 1..143；
  - 每个 `nb` 的值 == 该阶下组目录数（索引自洽）；
  - 数据总字节 28536355、按路径排序的整体拼接 sha256 与 6 个分类拼接 sha256
    等于官方源 galpol.tgz 的基线指纹；
  - 8 个单文件 sha256 抽查、GP 文本语法全量校验（real/complex 为
    `[Pol([...]),den]`、name 为带引号串、nb 为整数）、无 gzip 等意外文件混入。
丢/错/换任一字节都会让 test_verify.py 返回非 0，conan create 的 test 阶段即失败。
"""
import os

from conan import ConanFile


class PariGalpolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["pari-galpol"].package_folder
        galpol = os.path.join(pkg, "res", "pari", "galpol")
        script = os.path.join(self.source_folder, "test_verify.py")
        # R34: 校验被测包真实打包内容。数据校验与 host-python 无关目标架构，直接执行。
        self.run(f'python3 "{script}" "{galpol}"', env="conanrun")
