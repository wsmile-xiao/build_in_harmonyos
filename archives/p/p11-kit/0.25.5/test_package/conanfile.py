#!/usr/bin/env python3
"""Conan test_package — p11-kit 0.25.5（dlopen 探针模式）

采用 libgpg-error 1.55 已验证的探针写法：直接编译 test.c（-ldl），
运行时 dlopen 被测包 .so 并 dlsym 真实导出符号（R34 反空壳）。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class P11KitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["p11-kit"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libp11-kit.so")
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
