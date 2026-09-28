#!/usr/bin/env python3
"""Conan test_package — OCaml 4.14.4

Verifies that ocaml is installed and can report its version.
"""
import os

from conan import ConanFile


class OcamlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 显式解释器调用 test.sh（OHOS hmmac 拒绝直执行 shebang 脚本），
        # bin 目录由 package_folder 显式传入，不依赖 PATH，无硬编码本机路径；
        # 第二个参数为 hello.ml 源码路径，用于 ocamlopt native 功能测试
        test_sh = os.path.join(self.source_folder, "test.sh")
        hello_ml = os.path.join(self.source_folder, "hello.ml")
        bin_dir = os.path.join(self.dependencies["ocaml"].package_folder, "bin")
        self.run(f'/bin/sh "{test_sh}" "{bin_dir}" "{hello_ml}"', env="conanrun")
