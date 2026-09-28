#!/usr/bin/env python3
"""Conan test_package — kaldi/g20231112 消费者视角验证（L1）。

不使用 CMakeDeps：Conan 把 OHOS 映射成 CMAKE_SYSTEM_NAME=HarmonyOS，CMake 没有该平台
模块（"System is unknown to cmake"），find_library 找不到 libkaldi-*.a。本仓 openblas 等
配方同样采用“直接用编译器 + 依赖 cpp_info 路径”的方式，这里沿用该约定。

- test_kaldi：真实链接 kaldi 静态库并调用 API（BLAS/LAPACK/kaldi 数学），断言数值结果。
- libkaldi_ohos_probe.so：验证 kaldi 静态库可链入共享库（消费方 libvosk.so 的用法）。
- test_ohos_kaldi.sh：鸿蒙特有测试（平台/ABI/头文件/dlopen 真机验证）。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class KaldiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # 构建产物落到 build/ 子目录（仓库 .gitignore 覆盖 build/），不污染配方目录。
        basic_layout(self)

    def _compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        return compilers.get("cpp", "/data/service/hnp/bin/clang++")

    def _flags(self):
        kaldi = self.dependencies["kaldi"].cpp_info
        openfst = self.dependencies["openfst"].cpp_info
        openblas = self.dependencies["openblas"].cpp_info

        inc = " ".join(f"-I{p}" for p in
                       list(kaldi.includedirs) + list(openfst.includedirs)
                       + list(openblas.includedirs))
        libdirs, seen = [], set()
        for p in list(kaldi.libdirs) + list(openfst.libdirs) + list(openblas.libdirs):
            if p not in seen:
                seen.add(p)
                libdirs.append(f"-L{p}")
        # 静态链接顺序：被依赖者靠后。kaldi 静态库 -> openfst（fstscript 依赖 fst）-> openblas。
        libs = " ".join(f"-l{l}" for l in kaldi.libs)
        libs += " " + " ".join(f"-l{l}" for l in reversed(list(openfst.libs)))
        libs += " " + " ".join(f"-l{l}" for l in openblas.libs)
        link = " ".join(libdirs) + f" {libs}"
        rpath = f"-Wl,-rpath,{openblas.libdirs[0]}"
        return inc, link, rpath

    def build(self):
        cxx = self._compiler()
        inc, link, rpath = self._flags()
        base = f"-std=c++17 -O1 {inc}"

        # 消费者功能测试（可执行文件）
        self.run(f'{cxx} {base} "{os.path.join(self.recipe_folder, "test_kaldi.cc")}" '
                 f'-o test_kaldi {link} {rpath} -lm -lpthread -ldl')
        # 鸿蒙场景：静态库链入共享库
        self.run(f'{cxx} {base} -fPIC -shared '
                 f'"{os.path.join(self.recipe_folder, "test_ohos_probe.cc")}" '
                 f'-o libkaldi_ohos_probe.so {link} {rpath} -lm -lpthread -ldl')

    def test(self):
        kaldi_pkg = self.dependencies["kaldi"].package_folder
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        self.run(f'"{os.path.join(self.build_folder, "test_kaldi")}"')
        self.run(f'{bash} "{os.path.join(self.recipe_folder, "test_ohos_kaldi.sh")}" '
                 f'"{kaldi_pkg}" "{self.build_folder}"')
