#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for spline 1.2 — Akima spline interpolation (aspline).

`spline` 提供 `aspline(1)`：从若干 (x, y) 数据点（文件或 stdin）拟合
**Akima 样条**并输出近似等间距的插值点，输出集**包含原始输入点**。

Akima 样条相比普通三次样条的优势是**不会在数据点之间产生多余的摆动**
（overshoot），更接近手绘曲线；代价是二阶导数不连续。数据集之间用空行分隔。

OHOS 适配 (aarch64 musl):
- 两个 .c 文件（aspline.c + utils.c）+ utils.h，无外部依赖（仅 libc + libm）
- ★ 上游 Makefile 的 CFLAGS 含 `-mfpmath=sse`（**x86 专有**）以及一长串告警
  开关，在 aarch64 上无法使用；build() 直驱 clang 绕开整条 Makefile
- 上游 Makefile 需要 `-D_GNU_SOURCE -DHAVE_GETLINE -DVERSION=\"1.2\"` 三个宏，
  直编时需显式补上（否则 getline 未声明 / 版本串为空）
- 链接 libm（`-lm`；musl 下数学函数在 libc 内，`-lm` 为兼容空壳）
- 产出单可执行文件 bin/aspline
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class SplineConan(ConanFile):
    name = "spline"
    version = "1.2"
    description = ("Akima spline interpolation: fit a smooth curve through (x, y) "
                   "points without the overshoot of cubic splines (aspline)")
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/spline"
    topics = ("spline", "akima", "interpolation", "math", "plot", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 不用上游 Makefile：其 CFLAGS 含 -mfpmath=sse（x86 专有）与大量告警开关。
        # 直编需补上游 Makefile 里的 DEFS：_GNU_SOURCE / HAVE_GETLINE / VERSION。
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "")
        self.run(f'{cc} {cflags} -O2 -w -std=gnu99 -D_GNU_SOURCE -DHAVE_GETLINE '
                 f'-DVERSION=\\"1.2\\" -o aspline aspline.c utils.c -lm')

    def package(self):
        copy(self, "aspline", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "aspline.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "spline"))
        copy(self, "CREDITS", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "spline"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
