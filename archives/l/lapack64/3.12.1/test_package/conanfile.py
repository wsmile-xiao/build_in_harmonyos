#!/usr/bin/env python3
"""Conan test package - lapack64 3.12.1: 真实消费者直编直链，验证 ILP64 数值断言"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译+链接（非 dlopen）：调用 liblapack64 的 Fortran 符号并链接
        # 全部传递依赖（cblas64 的 libblas64 + Fortran 运行时）——CI 的 L1e
        # 破坏性反向验证会把包目录移走再跑一次，链接真实依赖才不会被判成
        # 假测试。链接顺序：被测包在前（lapack64 引用 blas64 符号，单遍
        # 链接器从左到右解析），传递依赖随后。
        tested = "lapack64"
        libdirs = list(self.dependencies[tested].cpp_info.libdirs)
        libs = list(self.dependencies[tested].cpp_info.libs)
        incdirs = list(self.dependencies[tested].cpp_info.includedirs)
        for name, dep in self.dependencies.items():
            if not dep.cpp_info.libs:
                continue
            if getattr(getattr(dep, "ref", None), "name", None) == tested:
                continue
            libdirs.extend(dep.cpp_info.libdirs)
            libs.extend(dep.cpp_info.libs)
            incdirs.extend(dep.cpp_info.includedirs)
        inc = " ".join("-I" + p for p in incdirs)
        libdir_args = " ".join("-L" + p for p in dict.fromkeys(libdirs))
        lib_args = " ".join("-l" + l for l in libs)
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "/data/service/hnp/bin/clang")
        self.run("{cc} test.c -o test_probe {inc} {libdir_args} {lib_args} -lm"
                 .format(cc=cc, inc=inc, libdir_args=libdir_args, lib_args=lib_args))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} -c './test_probe'".format(bash), env="conanrun")
