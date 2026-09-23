#!/usr/bin/env python3
"""Conan test_package — pip-completion 20200731 (Conan L1 test).

纯 bash 补全脚本包没有可执行文件可跑，因此这里以“消费者视角”真实加载被测脚本：
  1. 断言安装产物存在且非空；
  2. bash -n 语法校验；
  3. source 后 `complete -p pip` 必须输出 `complete -o default -F _pip pip`
     （等价 Homebrew Formula 的 test do 断言）；
  4. 用固定 help 输出的 pip 桩驱动被测的 _pip() 函数，断言补全候选被真实生成
     （不依赖机器上是否安装 pip，保证 CI 可复现）。
所有断言都在 test_completion.sh 内，由 self.run 真实执行（R34）。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class PipCompletionTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["pip-completion"]
        resdir = str(dep.cpp_info.resdirs[0])
        completion_file = os.path.join(resdir, "bash-completion", "completions", "pip")
        test_script = os.path.join(self.source_folder, "test_completion.sh")
        # 路径加引号：包目录可能含空格（与同族先例一致的语义，避免 shell 拆词）
        self.run(f'bash "{test_script}" "{completion_file}"')
