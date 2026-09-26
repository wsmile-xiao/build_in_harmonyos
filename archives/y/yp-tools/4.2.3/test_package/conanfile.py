#!/usr/bin/env python3
"""test_package — yp-tools 4.2.3（CLI 工具集，消费者视角验证）。

分工：
  * 上游官方测试（lib/xdrfile-test）在 conanfile.py 的 build() 中以
    `make check` 执行（manifest: upstream_test_in_build=true）。
  * 本 test_package 验证"消费者实际拿到的 9 个上游工具样例"是否可用，
    并额外验证鸿蒙（musl libc / HMDFS）适配约束（OHOS-specific 用例）。

判定入口为 test_yp_tools.sh：逐条打印 PASS/FAIL/SKIP，任一 FAIL → 非零退出。
"""
import os

from conan import ConanFile


class YpToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["yp-tools"]
        harness = os.path.join(self.recipe_folder, "test_yp_tools.sh")
        self.run(f'/bin/sh "{harness}" "{dep.package_folder}"')
