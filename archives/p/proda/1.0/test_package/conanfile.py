#!/usr/bin/env python3
"""Conan test_package for proda 1.0.

proda 是 package_type="application"：上游不产出 .a/.so、不装任何头文件，
使用这个包的唯一方式就是**调用被装进包目录 bin/ 的 proda 可执行文件**。
因此本 test_package 不做"include 一下 / 链接一下 / 打印一下"这类假消费者
动作，而是用 run_tests.sh 以真实使用者身份驱动 proda 做概率多序列比对，
14 个场景 31 条断言，全部由**退出码 + 对输出内容的判定**决定成败，
其中含 3 组负向对照（阈值过大 / 序列不相关 / 文件缺失时**不得**产出比对块）。

R34 口径：test() 必须真的把被测包产物执行起来 —— 这里 proda 由
VirtualRunEnv 放到 PATH 上，run_tests.sh 直接调 `proda`，跑不到就 exit 1。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout

# 通过下限：与 test_package/MANIFEST.yml 的 assertion_count、
# run_tests.sh 自己打印的 ASSERTIONS、notes.md 的五维账本四处逐字同源。
SCENARIOS = 14
MIN_PASS = 31


class ProdaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # application 包：没有可链接的产物，无需编译消费者程序。
        pass

    def test(self):
        script = os.path.join(self.recipe_folder, "run_tests.sh")
        # 设备上没有 /bin/bash（只有 /bin/sh），一律用显式 `sh` 前缀调用，
        # 不依赖 shebang 解释器路径；/tmp 只读，故 run_tests.sh 内部把工作
        # 目录取 ${TMPDIR:-$PWD}。
        self.run('MIN_PASS=%d sh "%s"' % (MIN_PASS, script), env="conanrun")
