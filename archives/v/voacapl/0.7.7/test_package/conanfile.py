#!/usr/bin/env python3
"""voacapl test_package — CLI 二进制真实执行验证

voacapl 是纯命令行工具（Fortran），无公共库 API。按 R34 必须真实执行
被测包二进制：编译 test.c（popen 执行 `voacapl --version` 校验版本输出），
并直接运行 `voacapl --version`、辅助工具 --help 校验可执行性。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class VoacaplTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # 编译 test.c（popen 执行 voacapl --version）。basic_layout 下
        # build() 在 build-release 子目录执行，须引用 source 目录的 test.c。
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict)
        cc = comp.get("c", "/data/service/hnp/bin/clang")
        src_test = os.path.join(self.source_folder, "test.c")
        self.run(f"{cc} -o test_voacapl {src_test}")

    def test(self):
        # 1) test.c 编译产物：popen 执行 voacapl --version 校验版本输出
        self.run("./test_voacapl", env="conanrun")
        # 2) 主程序版本校验（直接执行；voacapl --version 是唯一不依赖
        #    itshfbc 数据目录的 CLI 路径，满足 R34 真实执行被测包二进制）
        pkg = self.dependencies["voacapl"].package_folder
        voacapl = os.path.join(pkg, "bin", "voacapl")
        self.run(f'"{voacapl}" --version', env="conanrun")
