#!/usr/bin/env python3
"""Conan test_package — packcc 3.1.0 消费者冒烟（R34 / L0c）。

test() 以 self.run 调用真实测试脚本 run_test.sh（bash），对安装产物 packcc
执行真实任务：
  1. ``packcc --version``                       → 可执行文件存在、可运行、版本 3.1.0
  2. ``packcc -o calc_parser calc.peg``         → 从 grammar 真实生成 parser
  3. 断言 calc_parser.c / calc_parser.h 已生成  → 生成器非空壳、输出落盘
任何一步失败 conan create 即失败。
"""
import os

from conan import ConanFile


class PackccTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # run_test.sh 与 calc.peg 同目录（source_folder）；脚本以 CWD=build_folder
        # 运行，生成的 calc_parser.c/.h 落在 build_folder，脚本内断言有效。
        script = os.path.join(self.source_folder, "run_test.sh")
        self.run(f'bash "{script}"', env="conanrun")
