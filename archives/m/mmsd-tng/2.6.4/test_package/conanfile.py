#!/usr/bin/env python3
"""Conan consumer test — mmsd-tng 2.6.4（L1 官方测试 / R34：实质调用被测包产物）。

mmsd-tng 是应用型包（只产出可执行文件 mmsdtng / mmsctl），因此本测试不链接库，
而是在**真实运行期环境**（VirtualRunEnv 的 conanrun，含依赖共享库路径）中实际
执行被测产物，并校验 OHOS 目标 ABI / 加载器可解析性。

用例清单见 test_mmsd_tng.py 头部注释，其中 2 项为【HarmonyOS 专属】用例。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class MmsdTngTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            # 交叉编译场景：本机无法执行目标产物（本平台为 OHOS aarch64 原生构建，正常会进入下面的实跑）
            self.output.warning("can_run() = False — skip runtime test cases")
            return
        pkg_folder = self.dependencies["mmsd-tng"].package_folder
        script = os.path.join(self.source_folder, "test_mmsd_tng.py")
        self.run(f'"{sys.executable}" "{script}" "{pkg_folder}"', env="conanrun")
