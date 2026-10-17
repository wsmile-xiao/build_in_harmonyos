#!/usr/bin/env python3
"""test_package for sexpp-cli 0.9.2 — 消费者视角真实执行 sexpp CLI（PF3/L0c）。"""
import os

from conan import ConanFile


class SexppCliTestConan(ConanFile):
    """运行 test.sh：帮助输出 + canonical/advanced 解析回打（3 项断言）。"""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # PF3: 必须通过 self.run 实际执行被测包安装出的 sexpp 二进制。
        # OHOS: /system/bin/sh (mksh) 执行复合脚本不可靠，用 bash 包一层（aa3d/2048 先例）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
