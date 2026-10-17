#!/usr/bin/env python3
"""test_package — potool 0.19（可执行包，消费者视角真跑）。

CI 通过 `conan create` 自动执行本 L1 测试（PF3: test() 必须有 self.run 实际执行）。
断言点见 test.sh（共 5 条），其中第 4/5 条是鸿蒙适配特有断言（可移植 shebang 已进产物）。
"""
import os

from conan import ConanFile


class PotoolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (toybox) 执行 ELF 与 POSIX 细节有差异，统一用 bash 包一层。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
