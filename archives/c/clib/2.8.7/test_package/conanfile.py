#!/usr/bin/env python3
# conanfile.py — test_package for clib 2.8.7
#
# clib 是命令行工具(package_type=application):无公开库 API 可链接,
# 消费者验证走真实命令行为(catpoint 工具包先例):
#   1. clib --version / usage 输出
#   2. clib <command> 经 which() 在 PATH 找 clib-<command> 的分发机制
#      (conanrun env 注入包 bindir,子命令可真实分发执行)
#   3. clib init 端到端生成 clib.json
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class ClibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        # workflow §5.3: test_package 必须显式定义 layout(),
        # 否则 build_folder==source_folder,env 脚本直接落进包源目录
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        # basic_layout 下 test() 的 cwd 是 build 子目录,按 catpoint 先例
        # 用源目录绝对路径执行 test.sh
        test_sh = os.path.join(os.path.dirname(__file__), "test.sh")
        self.run(f"{bash} '{test_sh}'", env="conanrun")
