#!/usr/bin/env python3
"""Conan test_package — letter-shell 3.1.2.

L1 官方测试：消费者视角验证 libletter-shell.a 可链接、可调用真实 Shell API
(shellInit/shellRun/SHELL_EXPORT_CMD)，并通过 shellCommand 段链接脚本运行命令。
同时编译运行 HarmonyOS 专项测试 (test_ohos.c)。
"""
import os

from conan import ConanFile


class LetterShellTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        pass

    def build(self):
        dep = self.dependencies["letter-shell"]
        inc = os.path.join(dep.package_folder, "include")
        lib = os.path.join(dep.package_folder, "lib")
        lds = os.path.join(dep.package_folder, "lib", "shellcmds.lds")
        cc = "clang"
        # 消费者测试：真实调用公开 API（shellInit/shellRun/命令行执行）
        self.run(f"{cc} -I{inc} test.c {lib}/libletter-shell.a "
                 f"-Wl,-T,{lds} -o test_letter-shell")
        # HarmonyOS 专项测试：aarch64 平台断言 + shell 命令执行验证
        self.run(f"{cc} -I{inc} test_ohos.c {lib}/libletter-shell.a "
                 f"-Wl,-T,{lds} -o test_letter-shell_ohos")

    def test(self):
        self.run("./test_letter-shell", env="conanrun")
        self.run("./test_letter-shell_ohos", env="conanrun")