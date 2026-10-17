#!/usr/bin/env python3
"""Conan recipe for cct 1.0.0 — C/C++ 进制/计算工具（CLI）。

cct（Sife-shuo/cct，"A C/C++ Calc Tool"）是极简 C++ CLI 计算工具
（进制转换/位运算等），纯标准库（iostream/string/vector），无任何
Conan 依赖。源码树仅 main.cpp + 3 个 header（bit.hpp/command.hpp/
dem.hpp），无 Makefile/CMake——README 编译命令 `g++ main.cpp -o
cct`。

Upstream: Sife-shuo/cct tag 1.0.0（与清单版本一致——无需按最新版）。

Build:   clang++ -std=c++17 main.cpp → bin/cct（OHOS 编译器路径从
         conan conf 读取，同 jack/1.9.22 先例）。
Install: bin/cct。
Type:   application（CLI 工具——commands.json 软件级声明）

Deps:   无（纯标准库）。

上游测试: test/test.cpp（_cmd_parse 解析 "d 2 10 10100011" 的
         printv 输出）——本地实跑。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class CctConan(ConanFile):
    name = "cct"
    version = "1.0.0"
    description = "C/C++ Calc Tool — 进制转换/位运算 CLI 计算工具"
    license = "MIT"
    homepage = "https://github.com/Sife-shuo/cct"
    url = "https://github.com/Sife-shuo/cct"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL 含 /tar.gz/ 段——conan get() 误判为 zip 报
        # BadZipFile（batsignal/c4project 同款）——显式 filename 指定
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="cct-1.0.0.tar.gz")

    def _cxx(self):
        # OHOS 编译器（clang++）位于 /data/service/hnp/bin/，不在默认
        # PATH 中——从 conan conf 读取（jack/1.9.22 先例）
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("cpp") or "clang++"

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        # README 编译命令：g++ main.cpp -o cct——clang++ 同款
        self.run(
            f'"{self._cxx()}" -std=c++17 -O2 '
            f'{os.path.join(self.source_folder, "main.cpp")} '
            f'-o {os.path.join(self.source_folder, "cct")}',
            cwd=self.source_folder,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "cct", src=self.source_folder, dst=bindir)

    def package_info(self):
        self.output.info("cct 1.0.0: bin/cct")
        # R38 — CLI 工具
        self.conf_info.define("user.tools.cct:exe", "cct")
