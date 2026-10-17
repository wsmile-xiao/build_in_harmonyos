#!/usr/bin/env python3
"""Conan test_package — cranium-ml L1 消费者 + 鸿蒙专项测试。

编译并真实调用 cranium 公开 API：
 1. test_package.c       — 消费者验证（矩阵运算 + 网络前向公开 API 行为断言）
 2. ohos_special_test.c  — HarmonyOS 专项测试（XOR 训练收敛断言，走公开训练 API）
"""
from conan import ConanFile
from conan.tools.build import cross_building
import os


class CraniumMlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _build_one(self, src, out):
        cc = os.environ.get("CC", "clang")
        include = os.path.join(self.dependencies["cranium-ml"].package_folder, "include", "cranium")
        self.run("{cc} -std=c99 -Wall -I{include} -o {out} {src} -lm".format(
            cc=cc, include=include, out=out, src=src))

    def build(self):
        self._build_one(os.path.join(self.source_folder, "test_package.c"), "test_package")
        self._build_one(os.path.join(self.source_folder, "ohos_special_test.c"), "ohos_special_test")

    def test(self):
        if not cross_building(self):
            self.run("./test_package")
            self.run("./ohos_special_test")