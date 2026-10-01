#!/usr/bin/env python3
"""Conan recipe for piler 0-20140707 (PILER 1.0) — OHOS (HarmonyOS PC) aarch64.

Upstream : https://www.drive5.com/piler/   (Robert C. Edgar, public domain)
Package  : 单个命令行工具 `piler2` —— 基因组重复序列分析（dispersed repeat /
           CRISPR / LTR / tandem array 检测）。约 40 个 C++ 翻译单元 +
           手写 Makefile，除 libc/libm 外无任何第三方依赖。

OHOS 适配（见 patches/0001-ohos-makefile-toolchain-hardening.patch）
  1. 上游 Makefile 硬编码 `GPP = g++`。OHOS aarch64 工具链只提供 clang++
     （无 g++），原样构建立即失败（`g++: No such file or directory`，make
     Error 127）。改为 `GPP = $(CXX)`，编译器由 Conan 的
     `tools.build:compiler_executables` 提供（R33：禁止依赖 shell 环境变量）。
  2. 上游 `CFLAGS = ...` / `LDLIBS = -lm -static` 为硬赋值，会丢弃工具链传入
     的 CFLAGS/LDFLAGS。改为 `CFLAGS +=` / `LDLIBS = $(LDFLAGS) ...`。
  3. 上游 `-static` 产出非 PIE 的 `ET_EXEC`（readelf: Type EXEC），不满足
     鸿蒙硬化基线（conan-verify L4 报 "PIE disabled"；Debian 打包同样移除了
     `-static`）。上游"自包含单文件二进制"的意图需要保留，故改用
     `-static-pie`：既无 DT_NEEDED（不依赖设备上无保证的共享 libc++），
     又产出 PIE + full RELRO + NX。

上游测试
  tarball 内**没有**任何自动化测试：无 tests/ 目录、Makefile 无 check/test
  目标、无 ctest/pytest、无样例数据。配方不伪造上游测试，功能覆盖由
  test_package/test.sh 按上游 User Guide 的全部工作流补全（16 项），
  并在 test_package/conanfile.py 中追加 2 项 OHOS 适配专项用例。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class PilerConan(ConanFile):
    name = "piler"
    version = "0-20140707"
    description = ("PILER -- parsimonious inference of a library of elementary "
                   "repeats; genomic repeat analysis command line tool (piler2)")
    license = "public-domain"
    homepage = "https://www.drive5.com/piler/"
    url = "https://www.drive5.com/piler/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS 与 Linux 同族判断，禁止 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "piler is only supported on Linux/OHOS, not %s" % self.settings.os)

    def layout(self):
        basic_layout(self)

    def source(self):
        # 上游 tarball 是 flat 归档（无顶层目录包裹），strip_root 必须为 False
        get(self, **self.conan_data["sources"], strip_root=False)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器来自 Conan 工具链配置，不读 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        cxx = (compilers.get("cpp") or "").strip() or "clang++"
        self.output.info("Using C++ compiler: %s" % cxx)
        # R9: 固定 -j1
        self.run('make CXX="%s" -j1' % cxx, cwd=self.source_folder)

    def package(self):
        copy(self, "piler2", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
