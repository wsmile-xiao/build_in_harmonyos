#!/usr/bin/env python3
"""lpac test_package — 真实执行被测二进制 lpac 并断言其行为（R34 / PF3）。"""
import os

from conan import ConanFile


class LpacTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 被测包的 package_folder 从依赖图取（test_package 已 requires tested_reference），
        # 不用 self.package_folder —— 无 layout() 时后者会解析成 test_package 自己的目录
        # （第 6 轮实测报错路径是 `…/test_package/bin/lpac: inaccessible or not found`）。
        try:
            pkg = self.dependencies["lpac"].package_folder
        except Exception:
            pkg = self.package_folder
        lpac = os.path.join(pkg, "bin", "lpac")
        script = os.path.join(os.path.dirname(__file__), "test.sh")
        # self.run 实际执行被测二进制（PF3 硬闸要求 test() 内有 self.run）
        self.run("sh {} \"{}\"".format(script, lpac), env="conanrun")
