#!/usr/bin/env python3
"""test_package — asterisk-espeak 5.0 consumer test (R34 合规).

L1 test:
1. 编译 test.c（真实编译，非空壳）并运行——dlopen 加载 app_espeak.so
   （Asterisk eSpeak 模块），验证模块可加载且 espeak-ng/libsamplerate
   依赖可解析；失败即返回非零。
"""
import os

from conan import ConanFile


class AsteriskEspeakTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式 requires（test() 需用依赖包路径组装 LD_LIBRARY_PATH）
        self.requires("espeak-ng/1.51")
        self.requires("libsamplerate/0.2.2", options={"shared": False})

    def build(self):
        # TMPDIR 注入（鸿蒙安全框架拦 clang 创建临时文件）
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_asterisk_espeak")
        pkg = self.dependencies["asterisk-espeak"].package_folder
        so_dir = os.path.join(pkg, "lib", "asterisk", "modules")
        self.run(
            f"{cc} {src} -o {out} -ldl "
            f"-Wl,-rpath,{so_dir} -Wl,-rpath-link,{so_dir}")

    def test(self):
        exe = os.path.join(self.build_folder, "test_asterisk_espeak")
        # test.c 用相对路径 fopen("app_espeak.so")——在模块目录内运行
        pkg = self.dependencies["asterisk-espeak"].package_folder
        so_dir = os.path.join(pkg, "lib", "asterisk", "modules")
        self.run(f"cd {so_dir} && {exe}", env="conanrun")
