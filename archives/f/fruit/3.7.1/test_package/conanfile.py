#!/usr/bin/env python3
"""Conan test_package for fruit 3.7.1.

Compiles a real consumer that links libfruit and exercises the public DI API
(Component/Injector/interface binding), then runs it on the target.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class FruitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_cc(self):
        for cand in ("clang++", os.environ.get("CXX", "")):
            if cand and shutil.which(cand):
                return cand
        return "clang++"

    def build(self):
        incs, libs, libdirs = [], [], []
        for _r, d in self.dependencies.items():
            incs += d.cpp_info.includedirs
            libs += d.cpp_info.libs
            libdirs += d.cpp_info.libdirs
        inc = " ".join("-I" + p for p in dict.fromkeys(incs))
        ldir = " ".join("-L" + p for p in dict.fromkeys(libdirs))
        lib = " ".join("-l" + l for l in dict.fromkeys(libs))
        cc = self._find_cc()
        # 消费者探针（公开 DI API 冒烟）
        self.run(f"{cc} -std=c++11 test_fruit.cpp -o test_fruit_probe {inc} {ldir} {lib}")
        # HarmonyOS 专项测试（multibindings + 注解注入 + 单例语义）
        self.run(f"{cc} -std=c++11 test_fruit_ohos.cpp -o test_fruit_ohos_probe {inc} {ldir} {lib}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verifying compile+link")
            return
        self.run("./test_fruit_probe", env="conanrun")
        self.run("./test_fruit_ohos_probe", env="conanrun")
