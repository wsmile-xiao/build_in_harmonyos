#!/usr/bin/env python3
"""Conan test package - cblas64 3.12.1: 真实消费者直编直链，验证 4 项手算断言"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译+链接（非 dlopen）：既 #include <cblas.h>（经 CBLAS_API64 拉起
        # cblas_64.h 的 _64 声明），又链接 libcblas64（依赖包的 lib/）——CI 的 L1e
        # 破坏性反向验证会把这两个目录整个移走再跑一次，两处都真实依赖才不会被判
        # 成假测试。libblas64/FortranRuntime/FortranDecimal 随包 cpp_info 一并链接。
        dep = self.dependencies["cblas64"].cpp_info
        inc = " ".join("-I" + p for p in dep.includedirs)
        libdir = dep.libdirs[0]
        libs = " ".join("-l" + l for l in dep.libs)
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "/data/service/hnp/bin/clang")
        # -DCBLAS_API64：cblas.h 以该宏拉起 cblas_64.h 的 cblas_*_64 声明
        self.run("{cc} -DCBLAS_API64 test.c -o test_probe {inc} -L{ld} -Wl,-rpath-link,{ld} {libs} -lm"
                 .format(cc=cc, inc=inc, ld=libdir, libs=libs))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} -c './test_probe'".format(bash), env="conanrun")
