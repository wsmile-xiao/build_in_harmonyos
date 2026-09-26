#!/usr/bin/env python3
"""Conan test_package — libindi 2.2.2.1 (Conan L1 official test).

R34 实质测试：调用 libindi 核心 C API（base64 编解码往返）并执行。
本机/CI 的 HMDFS 无法对 OHOS 共享库 mmap PROT_EXEC（E537/R49 教训，
知识图谱同款提示），故探针采用全静态链接（--gc-sections --as-needed，
实测仅依赖 libc.so 可运行）——argp-standalone test_package 已验证模式。
"""
import os

from conan import ConanFile


class LibindiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["libindi"].package_folder
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.recipe_folder, "test.c")
        out = os.path.join(self.build_folder, "test_libindi")
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        # 全静态链接：libindiclient.a/libindidriver.a + --gc-sections 丢弃
        # 未用依赖（base64 符号实测在二者中均有），规避共享库运行时加载
        self.run(
            f"{cc} {src} -o {out} -Wl,--gc-sections,--as-needed "
            f"-I{inc} {os.path.join(lib, 'libindiclient.a')} "
            f"{os.path.join(lib, 'libindidriver.a')} -lm"
        )
        self.run(out)
