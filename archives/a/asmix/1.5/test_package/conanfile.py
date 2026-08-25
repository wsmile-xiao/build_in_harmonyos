#!/usr/bin/env python3
"""Conan test_package — asmix 1.5 L1 冒烟测试 (R34 真实产物校验 + L0c 测试源).

asmix 为 X11 GUI 应用（OHOS 无显示环境无法运行 GUI 本体），二进制 -V 选项
在 X 连接前可运行，但 HMDFS 环境直接执行受限；按 R34 要求做**产物级真实
校验**：手动编译 test.c（读 ELF magic + e_machine 校验 arm64 ELF）为
test_asmix，test() 用 self.run() 执行该测试程序（满足 L0c 测试源 +
L0d self.run 门禁；不依赖 CMakeToolchain 生成器，避免 CMakePresets 问题）。
"""
import os

from conan import ConanFile


class AsmixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 手动编译测试源（test.c -> test_asmix），注入 asmix 二进制路径
        bin_path = os.path.join(self.dependencies["asmix"].package_folder, "bin", "asmix")
        self.output.info(f"asmix binary: {bin_path}")
        cc = os.environ.get("CC", "clang")
        self.run(
            f"{cc} -O2 -Wall test.c -o test_asmix "
            f"-DASMIX_BIN_PATH='\"{bin_path}\"'"
        )

    def test(self):
        # L0d 门禁要求 test() 调用 self.run() 执行测试程序
        self.run("./test_asmix")
