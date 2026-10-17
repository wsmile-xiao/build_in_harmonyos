#!/usr/bin/env python3
"""Conan test_package — termbg 0.6.2 消费者验证。

两层验证：

1. **消费者冒烟 + 鸿蒙特有检查**（``test_termbg.py``）：以消费者身份运行打包的
   ``bin/termbg``，断言真实行为——``--version``、默认检测输出、``COLORFGBG``
   环境变量回退路径（Dark/Light 两分支）、非法参数退出码；并断言产物是
   HarmonyOS aarch64 二进制（ELF e_machine=183 + ``/lib/ld-musl-aarch64.so.1``
   解释器 + ``.note.ohos.ident`` 段）——这是本平台可执行所必需的特性。
2. **上游测试证据重发**：``build()`` 已真实运行上游 ``cargo test`` 并把结果写入
   包内 ``res/upstream_test_result.json``；test_package 在**每次** preflight 都
   重新打印 ``HMBS_UPSTREAM_TEST_RESULT`` 标记（hmbs preflight 只从 test_package
   阶段 stdout 采集；conan 命中缓存跳过 build() 时仍需该标记 —— scooter/
   abuild-sudo 先例）。标记文件缺失 = 上游测试未运行 → 显式失败，绝不静默通过。
"""
import json
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TermbgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_termbg.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["termbg"].package_folder
        binary = os.path.join(package_folder, "bin", "termbg")
        if not os.path.isfile(binary):
            raise AssertionError(f"missing termbg executable: {binary}")

        if not can_run(self):
            self.output.info("cross-building: package layout verified only")
            return

        script = os.path.join(self.source_folder, "test_termbg.py")
        result = self.run(
            f'PACKAGE_FOLDER="{package_folder}" "{sys.executable}" "{script}"',
            env="conanrun", ignore_errors=True)
        if result != 0:
            raise AssertionError(
                f"termbg consumer tests failed with exit code {result}")

        # 上游测试证据（build() 真实运行结果，随包携带）
        evidence = os.path.join(package_folder, "res",
                                "upstream_test_result.json")
        if not os.path.isfile(evidence):
            raise ConanException(
                "res/upstream_test_result.json not found in package (%s) — "
                "upstream cargo test did not run during build(); refusing to "
                "pass silently" % evidence)
        with open(evidence, encoding="utf-8") as handle:
            upstream = json.load(handle)
        print("HMBS_UPSTREAM_TEST_RESULT="
              + json.dumps(upstream, ensure_ascii=False))
        if upstream.get("status") != "passed":
            raise ConanException(
                "upstream cargo test suite did not pass: %s" % upstream)
