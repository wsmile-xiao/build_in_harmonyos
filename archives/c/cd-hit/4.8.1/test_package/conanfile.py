#!/usr/bin/env python3
"""test_package for cd-hit — 真实功能测试（R34）。

执行 test.sh：真实调用 cd-hit 二进制对 3 条微型序列聚类，
断言 .clstr 输出为 2 簇（seq1+seq2 同簇 100%，seq3 独立簇）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CdhitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.skip_test("Cross-build: cannot run cd-hit")
        # OHOS /system/bin/sh (mksh) 不能执行 ELF 二进制；用 bash（参照 aaphoto 模式）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")