#!/usr/bin/env python3
"""Conan test_package for align 1.7.5.

L1 test: verify the align CLI tool runs and produces aligned output.
align is a Perl-script CLI tool (not a library), so test.c uses only
standard C and invokes the align binary via system().
"""
import os

from conan import ConanFile


class AlignTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # R33: 从 Conan conf 获取编译器（dict 形式，兼容 conan 2.29.1），避免依赖 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run(f"{cc} test.c -o test_align")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so wrap
        # binary execution with bash.
        bash = os.environ.get("CONFIG_SHELL") or next(
            (p for p in (
                "/data/service/hnp/bin/bash",
                "/bin/bash",
                "/usr/bin/bash",
            ) if os.path.exists(p)),
            "bash",
        )
        # align 是 Perl 脚本工具包，VirtualRunEnv 不自动把 bin 加入 PATH，
        # 显式将 package bin 目录加入 PATH 再运行 test_align，避免命中系统命令。
        pkg_folder = self.dependencies["align"].package_folder
        align_bin = os.path.join(pkg_folder, "bin")
        self.run(
            f"PATH={align_bin}:$PATH {bash} -c './test_align'",
            env="conanrun",
        )
