#!/usr/bin/env python3
"""Conan test_package — pakchois 0.4（dlopen 探针模式）

直接编译 test.c（链接 -ldl），运行期 dlopen 被测包 lib/libpakchois.so 并
dlsym 真实导出符号 pakchois_module_load / pakchois_get_info /
pakchois_module_destroy（R34 反空壳，参照 p11-kit 0.25.5 test_package）。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class PakchoisTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        # R33: 编译器取自 conan conf（profile tools.build:compiler_executables），
        # 不要裸用 ${CC}。test_package 未用 AutotoolsToolchain，故手动读取。
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        cc = compilers.get("c") if compilers else None
        return cc or os.environ.get("CC") or "clang"

    def build(self):
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        dep = self.dependencies["pakchois"].cpp_info
        so = os.path.join(dep.libdirs[0], "libpakchois.so")
        cc = self._cc()
        self.run(f"{cc} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
