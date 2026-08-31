#!/usr/bin/env python3
"""Conan test_package — x3270 4.4ga6

R34: 实质测试 — 通过 test_smoke.sh 直接执行被测包二进制（--version），
无管道遮蔽退出码；包产物被移走时命令必然失败，
从而通过 CI L1e 破坏性反向验证（fake test 检测）。
"""
import os

from conan import ConanFile


class X3270TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 调用冒烟测试脚本：脚本直接执行被测包二进制（--version），
        # 产物被移除（L1e sabotage）时脚本必然失败 → 测试失败
        bin_dir = os.path.join(self.dependencies["x3270"].package_folder, "bin")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_smoke.sh")
        self.output.info(f"running smoke test: {script} {bin_dir}")
        self.run(f'sh "{script}" "{bin_dir}"', env="conanrun")
