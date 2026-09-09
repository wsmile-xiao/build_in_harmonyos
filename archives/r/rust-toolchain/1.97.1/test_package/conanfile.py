#!/usr/bin/env python3
"""Conan test_package — rust-toolchain 1.97.1 (tool_requires 验证).

验证捆绑工具链可用：rustc/cargo 版本、aarch64-unknown-linux-ohos 目标标准库
已安装，并能交叉编译并在本机运行 hello 程序。
"""
import os
import shlex

from conan import ConanFile


class RustToolchainTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_sh = os.path.join(self.source_folder, "test.sh")
        # 工具链 PATH/CARGO_HOME/RUSTUP_HOME 由 tool_requires 注入构建环境；
        # 路径含空格/括号需 shlex.quote（仓库目录 build_in_harmonyos-main (4)）
        self.run(f"{shlex.quote(bash)} {shlex.quote(test_sh)}", env="conanbuild")
