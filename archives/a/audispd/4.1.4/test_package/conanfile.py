#!/usr/bin/env python3
"""test_package — audispd 4.1.4 consumer test (R34 合规).

L1 test:
1. 编译 test.c（真实编译，非空壳）并运行——真实读取包内产物
   audisp-af_unix（audit 事件分发插件）并校验为有效 64 位 ELF；
2. 注：不能无参运行插件（需完整 audit 内核环境，鸿蒙无）。
"""
import os

from conan import ConanFile


class AudispdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # TMPDIR 注入（鸿蒙安全框架拦 clang 创建临时文件）
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_audispd")
        self.run(f"{cc} {src} -o {out}")

    def test(self):
        exe = os.path.join(self.build_folder, "test_audispd")
        # test.c 用相对路径 fopen("audisp-af_unix")——在包内 bin/ 目录运行
        pkg = self.dependencies["audispd"].package_folder
        bin_dir = os.path.join(pkg, "bin")
        self.run(f"cd {bin_dir} && {exe}", env="conanrun")
