#!/usr/bin/env python3
"""Conan test_package — cargo-bash-completions 1.97.0 (Conan L1 test).

纯 bash 补全脚本包没有可执行文件可跑，因此这里以“消费者视角”真实加载被测脚本：
  A1 安装产物存在且非空；
  A2 体积合理（防止截断/空文件入包）；
  A3 bash -n 语法校验；
  A4 负向：PATH 中无 cargo 时上游守卫生效，不注册补全；
  A5 source 后 `complete -p cargo` 输出 `complete -F _cargo cargo`；
  A6 用固定输出的 cargo 桩驱动 _cargo()，断言子命令候选被真实生成；
  A7 `cargo build --<TAB>` 产出子命令选项候选；
  A8 版本实证：`cargo build -<TAB>` 候选含 cargo 1.97 新增的 `-m` 短选项
     （对上一周期 0.97.0/Rust 1.96 的脚本该断言实测失败，故能真正区分版本）。
所有断言都在 test_cargo_completion.sh 内，由 self.run 真实执行（R34 / PF3）。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class CargoBashCompletionsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["cargo-bash-completions"]
        resdir = str(dep.cpp_info.resdirs[0])
        completion_file = os.path.join(resdir, "bash-completion", "completions", "cargo")
        test_script = os.path.join(self.source_folder, "test_cargo_completion.sh")
        # 路径加引号：包目录可能含空格（与同族先例一致，避免 shell 拆词）
        self.run(f'bash "{test_script}" "{completion_file}"')
