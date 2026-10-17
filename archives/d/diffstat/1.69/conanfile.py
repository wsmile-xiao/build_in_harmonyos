#!/usr/bin/env python3
"""Conan recipe — diffstat 1.69 (Autotools).

diffstat: diff statistics tool (pure C, std libs only).
OHOS 适配：E213（config.guess HarmonyOS 检测）+ E214（config.status
沙箱绕过：umask 022 + 循环重跑 + make top_srcdir 覆盖）。
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class DiffstatConan(ConanFile):
    name = "diffstat"
    version = "1.69"
    package_type = "application"

    description = "Diff statistics tool (pure C, std libs only)"
    homepage = "https://invisible-island.net/diffstat/"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        top = self.source_folder
        # E214: config.status 临时目录须在可写位置（$HOME 根目录 mktemp 受限）
        os.environ["TMPDIR"] = self.build_folder
        conf = "--prefix=/"
        self.run(f"cd {top} && CC=clang ./configure {conf}")
        # E214: config.status 首次生成 Makefile 可能为空（沙箱竞态），
        # 循环重跑直到非空（-s 检查）
        self.run(f"cd {top} && while [ ! -s Makefile ]; do "
                 f"TMPDIR={self.build_folder} sh ./config.status Makefile; done")
        # E214: Makefile 变量污染（top_srcdir 乱码），make 命令行覆盖 top_srcdir
        self.run(f"cd {top} && make top_srcdir={top} -j1")
        # 上游测试：make check（testing/run_test.sh，51 case 557 断言）
        self.run(f"cd {top} && make check top_srcdir={top}")

    def package(self):
        top = self.source_folder
        self.run(f"cd {top} && make install top_srcdir={top} "
                 f"DESTDIR={self.package_folder}")
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []