#!/usr/bin/env python3
"""Conan test_package for libjcat-tools 0.2.3 — 消费者视角验证（L1）。

验证内容（babl-tools/libjwt-tools 工具件先例模式）：
  1. jcat-tool 经 Conan bindirs 通道可达（包内 bin/jcat-tool 存在）；
  2. 合法的 OHOS aarch64 ELF（ELF64 / e_machine=183 / PT_INTERP / X_OK）；
  3. 真实执行 `jcat-tool --version`（R34：test() 有 self.run 实际执行
     逻辑）——本机若遇 OHOS 动态库加载限制（E488 同源：依赖 .so 的
     mmap EACCES / 'No such file'），降级为静态断言并如实记录环境限制
     （json-glib 1.10.6 本体 test_package 同款降级口径）。

上游 CLI 功能语义（info/verify 子命令）由上游 jcat-self-test 的 19 个
用例覆盖，其执行证据与环境限制逐项登记在 notes.md「上游测试」节。
"""
import json
import os
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import can_run, cross_building

TOOL = "jcat-tool"


class LibjcatToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    # 独立测试脚本（L0c：test 源文件 + self.run 执行）
    exports_sources = "test_libjcat_tools.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        pass

    def test(self):
        pkg = None
        for _ref, dep in self.dependencies.items():
            if dep.ref.name == "libjcat-tools":
                pkg = dep.package_folder
                break
        if not pkg:
            raise Exception("libjcat-tools package folder not found")

        script = os.path.join(os.path.dirname(__file__),
                              "test_libjcat_tools.py")
        if not can_run(self) or cross_building(self):
            self.output.info(
                "cross-building/cannot-run: verifying package layout only")
            self.run(f"{sys.executable} {script} {pkg} --static-only",
                     env="conanrun")
            return
        self.run(f"{sys.executable} {script} {pkg}", env="conanrun")
