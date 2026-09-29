#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe — rifiuti 20040505

rifiuti 解析 Windows 回收站的 INFO2 文件，逐条打印被删除记录的
（索引、删除时间、盘符、路径、大小）。

构建系统：源码包**顶层没有 Makefile**，唯一的构建文件是 `src/Makefile`（实测 215 字节 /
`wc -l` = 10 行 / 4 个目标，sha256 前缀 f3bb0732），内含**两条** gcc 编译命令：
`src/Makefile:4`（`install` → 产物 `rifiuti`）与 `src/Makefile:7`（`installwin` →
`-DCYGWIN` 产物 `rifiuti.exe`，CYGWIN 专用）。默认目标 `all: install` 只走第一条
⇒ 本配方复刻的就是第一条：

    all: install

    install:  rifiuti.c
	    gcc -o rifiuti rifiuti.c -lm -lc;cp rifiuti ../bin

编译器名是**字面量 `gcc`** —— 既没有 `$(CC)` 也没有 `CFLAGS` 变量，
所以 `make CC=<交叉 clang>` 这类命令行覆盖对上游 Makefile 完全不生效；
而 OHOS 设备上只有 clang（`command -v clang` = `/data/service/hnp/bin/clang`，`command -v gcc` 为空），
直接 `make` 必失败：一手复现实测 rc=2，stderr 三行 `/bin/sh: gcc: inaccessible or not found` +
`cp: bad 'rifiuti': No such file or directory` + `make: *** [Makefile:4: install] Error 1`
（分号续行使第二步 `cp` 再报一次，故末行是 `Error 1` 而**不是** `Error 127`）
—— 与本包版本级 manifest.yaml 的 knowledge_gained 条目同一实测口径。

⇒ 适配方式：build() 用 Conan conf 取到真正的交叉编译器（R33），
  **逐字复刻**上游那一行 gcc 命令（同样的 -lm -lc、同样的产物名 rifiuti），
  `cp rifiuti ../bin` 这一步由 conan 的 package() 承担（装到 bin/）。
  不改源码、不打补丁、不造假 gcc。

许可证：src/rifiuti.c 头部是 BSD-3-Clause 模板文本（源码即许可文本，
包内没有独立的 LICENSE 文件）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class RifiutiConan(ConanFile):
    name = "rifiuti"
    version = "20040505"
    description = (
        "Windows 回收站 INFO2 文件解析器 — 逐条打印被删除记录的索引、"
        "删除时间、盘符、路径与大小"
    )
    license = "BSD-3-Clause"
    homepage = "https://packages.debian.org/source/squeeze/rifiuti"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游只链接 libc/libm（-lm -lc），无任何外部依赖 —— W0 preflight 因此天然满足
        pass

    def layout(self):
        basic_layout(self)

    # R32: 平台判断用 in (...)，不写 == "Linux"
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "rifiuti supports Linux/OHOS only, got %s" % self.settings.os
            )

    def source(self):
        # 解包后目录名是 rifiuti_20040505_1（≠ 版本号），strip_root 把它去掉，
        # 于是 self.source_folder 下就是 CHANGES / Readme.txt / bin/ / src/
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # 本包无补丁；保留调用以对齐框架惯例

        # R33: 编译器一律从 Conan conf 取，绝不裸用 shell 的 ${CC}/${CFLAGS}
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp.get("c") or "clang"
        src = os.path.join(self.source_folder, "src")

        # 逐字复刻上游 src/Makefile:4（install 规则）的那条编译命令；同一个 Makefile 的
        # :7（installwin 规则，-DCYGWIN 产物 rifiuti.exe）是 CYGWIN 专用，默认目标不触发
        # （上游:4 = gcc -o rifiuti rifiuti.c -lm -lc）
        self.run('"%s" -o rifiuti rifiuti.c -lm -lc' % cc, cwd=src, env="conanbuild")

    def package(self):
        # 上游 install 规则的 `cp rifiuti ../bin` ⇒ 等价语义：装到 package/bin/
        copy(
            self,
            "rifiuti",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        # 命令行工具，不是库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
