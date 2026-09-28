#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for letterize 1.6 — phone-number to letter-mnemonic generator.

letterize 是 Eric S. Raymond 的小工具（BSD-2-Clause），把电话号码数字
展开成所有"可发音"的字母助记词（mnemonics），按美式电话键盘映射：

    2→ABC  3→DEF  4→GHI  5→JKL  6→MNO  7→PRS  8→TUV  9→XYZ

不属于该集合的字符（0、1、破折号、括号、字母本身）原样透传。程序内嵌一张
"可发音字母三元组"词表，只有所有三元组都在词表中候选才会输出，因此一个
7 位号码的 19,683 种组合通常会被筛到几十到几百条。

OHOS 适配 (aarch64 musl):
- 单 .c 文件（letterize.c），无外部库依赖（仅 libc: ctype/stdio/stdlib/string）
- 上游 Makefile 的 CFLAGS 含 `-Werror`，且 `all:` 目标还依赖 asciidoctor 生成
  `letterize.1`（man 页从 .adoc 生成）；两者在交叉编译环境里都会阻断构建，
  因此 build() 直驱 clang，只编译二进制
- 产出单可执行文件 bin/letterize
- ★ aarch64 Linux 默认 `char` 是 **unsigned**，而词表索引依赖字符值；
  实测 aarch64 与 x86-64 输出行数一致（234→13 / 5551234→78 / 5551234567→246），
  说明该实现对 char 符号性不敏感，无需 patch
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class LetterizeConan(ConanFile):
    name = "letterize"
    version = "1.6"
    description = ("Phone-number to letter-mnemonic generator (US keypad "
                   "2=ABC .. 9=XYZ, pronounceable-triple filtering)")
    license = "BSD-2-Clause"
    homepage = "https://gitlab.com/esr/letterize"
    topics = ("phone", "mnemonic", "vanity-number", "cli", "text")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 直驱 clang（conan 2.x self.run() 默认 cwd = source_folder）
        # 不用上游 Makefile：其 CFLAGS 含 -Werror，且 all: 目标要求 asciidoctor
        # 生成 man 页，交叉编译环境两者都不可用。
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "")
        self.run(f"{cc} {cflags} -O2 -std=gnu99 -o letterize letterize.c")

    def package(self):
        copy(self, "letterize", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "letterize.adoc", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "letterize"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share", "licenses"]
