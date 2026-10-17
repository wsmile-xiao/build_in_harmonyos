#!/usr/bin/env python3
"""Conan test_package — http-parser 2.9.4 消费者测试。

真实消费被测包：头文件包含 + 链接 libhttp_parser + 运行真实解析程序，
任何断言失败返回非 0（不允许只构建不运行）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["http-parser"].cpp_info
        # L1e 保护：显式校验包内 include/lib 目录存在，确保 test 依赖被测包产物
        for p in dep.includedirs:
            if not os.path.isdir(p):
                raise ConanException(f"http-parser package include dir missing: {p}")
        libdir = dep.libdirs[0]
        if not os.path.isdir(libdir):
            raise ConanException(f"http-parser package lib dir missing: {libdir}")
        inc = " ".join("-I" + p for p in dep.includedirs)
        # R33: 编译器从 Conan conf 获取，与配方本体保持一致
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # 编译 + 链接 + 生成真实消费者程序
        self.run(f"{cc} test_http_parser.c -o test_probe {inc} -L{libdir} -lhttp_parser")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: 只验编译+链接")
            return
        # 真实执行消费者程序（断言失败 → 非 0 退出码）
        self.run("./test_probe", env="conanrun")
