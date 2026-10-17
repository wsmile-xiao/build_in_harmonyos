#!/usr/bin/env python3
"""Conan test_package for nip4 9.1.5 — real snip CLI verification.

nip4 是 GTK4 应用（bin/nip4 GUI + bin/snip CLI）。上游完整测试套件（19+ 项）
已在 conanfile.py build() 中通过 `meson test` 运行（native OHOS 环境）。

本 test_package 从消费者视角做真实 CLI 冒烟：
  1. snip -e 表达式求值（'2 + 2' → 4、字符串、数组字面量），
     对应上游 test_cli.sh 的 check_output 断言。
  2. snip -w workspace 求值（读上游 test_cli.ws 的两格值）。
  3. snip -w workspace 保存 jpg（真实验证 vips JPEG 链路 + 写盘）。
  4. 验证产物为 OHOS aarch64 ELF（musl interpreter）。

注意：不静默跳过 —— 所有断言真实执行已安装的 snip 二进制。
"""
import os

from conan import ConanFile


class Nip4TestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["nip4"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        snip_path = os.path.join(bin_dir, "snip")

        this_dir = os.path.dirname(os.path.abspath(__file__))
        run_sh = os.path.join(this_dir, "run_tests.sh")
        work_dir = os.path.join(self.build_folder, "work")

        self.run(f'sh {run_sh} "{snip_path}" "{work_dir}"',
                 env="conanrun")
        self.output.info("nip4: OK")