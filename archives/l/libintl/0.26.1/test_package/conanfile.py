#!/usr/bin/env python3
"""Conan test_package for libintl — C 级验证（L1 official test）。

test_libintl.c 真实加载 libintl.so.8 并校验双符号集（R34 实质测试）。
用 self.run（L0d 要求）+ 命令内联 LD_LIBRARY_PATH。
"""
import os

from conan import ConanFile


class LibintlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["libintl"].package_folder
        libdir = os.path.join(pkg, "lib")
        src = os.path.join(os.path.dirname(__file__), "test_libintl.c")
        out = os.path.join(os.path.dirname(__file__), "test_libintl")
        cc = "/data/service/hnp/bin/clang"
        # 编译
        self.run(f"{cc} '{src}' -o '{out}' -ldl")
        # 运行（LD_LIBRARY_PATH 指向被测包 lib，含 libintl.so.8）
        self.run(f"LD_LIBRARY_PATH='{libdir}' '{out}'")
        # 校验软链 libintl.so → libintl.so.8
        if not os.path.lexists(os.path.join(libdir, "libintl.so")):
            raise Exception("libintl.so symlink missing")
        self.output.info("[PASS] libintl.so symlink present")
