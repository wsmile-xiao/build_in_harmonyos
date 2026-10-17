#!/usr/bin/env python3
"""test_package for wise 2.4.1 — 消费者视角真实功能测试（R34）。

在 conanrun 运行环境中执行 test.sh，即鸿蒙特有测试的 7 个完整端到端消费者用例：
HC-1 消费链路入口（11 个程序 PATH 定位 + 包导出的 WISECONFIGDIR 运行期数据 +
11 个 -version）、HC-2 genewise 蛋白×基因组 DNA、HC-3 estwise 蛋白×cDNA、
HC-4 dnal DNA×DNA、HC-5 psw 蛋白×蛋白、HC-6 dba DNA×DNA 块比对、
HC-7 promoterwise 双 DNA 启动子预测。每个用例都真实执行包内安装的二进制
并校验其真实输出，任一环节失败即该用例 FAIL。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class WiseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.skip_test("Cross-build: cannot run wise programs")
        # OHOS 的 /system/bin/sh (mksh) 不能直接执行 ELF 二进制，改用 bash
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
