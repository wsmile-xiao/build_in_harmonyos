#!/usr/bin/env python3
"""Conan test package - blas 3.12.1: 真实消费者直编直链，验证 4 项手算断言"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译+链接（非 dlopen）：链接依赖包的 lib/（CI 的 L1e 破坏性反向
        # 验证会把 lib 目录整个移走再跑一次，真实依赖才不会被判成假测试）。
        dep = self.dependencies["blas"].cpp_info
        libdir = dep.libdirs[0]
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "/data/service/hnp/bin/clang")
        self.run("{cc} test.c -o test_probe -L{ld} "
                 "-Wl,-rpath-link,{ld} "
                 "-lblas -lFortranRuntime -lFortranDecimal -lm".format(
                     cc=cc, ld=libdir))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} -c './test_probe'".format(bash), env="conanrun")