#!/usr/bin/env python3
"""Conan test_package for afsp 8.2 — 验证 InfoAudio 工具可执行。

AFsp 是音频工具集（application），上游测试已在 build() 阶段运行
（txxxAudio 6 段功能测试全部通过）。test_package 运行 InfoAudio --help
验证二进制已安装到 bin/ 且可执行（R34 反空壳：真实调用被测包二进制）。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class AfspTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        bin_dir = self.dependencies["afsp"].cpp_info.bindirs[0]
        pkg = self.dependencies["afsp"].package_folder
        info_audio = os.path.join(pkg, bin_dir, "InfoAudio")
        if not os.path.exists(info_audio):
            raise Exception(f"InfoAudio not found at {info_audio}")
        # R34 反空壳：真实执行 InfoAudio --help（L0d 门禁要求 test() 有 self.run 调用）
        self.run(f'"{info_audio}" --help')
        self.output.info("afsp test PASSED (InfoAudio --help runs)")
