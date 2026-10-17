#!/usr/bin/env python3
"""test_package — picotool 2.2.0 consumer test (R34).

L1 test:
1. 编译并运行 test.c（校验包内 bin/picotool 为有效 64 位 ELF——
   同 audispd/asterisk-espeak 先例）。
"""
import os

from conan import ConanFile


class PicotoolTestConan(ConanFile):
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
        out = os.path.join(self.build_folder, "test_picotool")
        self.run(f"{cc} {src} -o {out}")

    def test(self):
        # cd 到包目录（bin/picotool 相对路径从包根解析）
        pkg = self.dependencies["picotool"].package_folder
        exe = os.path.join(self.build_folder, "test_picotool")
        os.chdir(pkg)
        self.run(exe)
