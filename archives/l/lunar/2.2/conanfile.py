#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for lunar 2.2 — Chinese Lunar Calendar conversion utility.

lunar 是 Fung F. Lee / Ricky Yeung 的经典农历换算工具（GPL-2.0-or-later，
1988-2001），在公历（Solar Calendar）与中国农历（Lunar Calendar，北京时间）
之间双向换算，并给出：

- ShengXiao（生肖）
- GanZhi（干支：年/月/日/时四柱，GanZhi Order 与 JiaZi Cycle 两套编号）
- BaZi（八字，"Four Column Calculation"）
- 闰月（run-yue）标注与农历→公历的反查

OHOS 适配 (aarch64 musl):
- 单 .c 文件（lunar.c + tables.h），无外部库依赖（仅 libc: stdio/string）
- 代码为 K&R 风格函数定义，clang 15 默认 gnu17 下可直接编译
- 直驱 clang 编译（不调 Makefile，避免 Makefile 里硬编码 `cc`），
  产出单可执行文件 bin/lunar
- 上游 Makefile 的 `lunar: lunar.o` 目标用裸 `cc`，且 `clean` 用 `rm *.o`，
  在 conan 交叉编译环境里两条都不可靠，因此 build() 直接调 clang
- -b（bitmap 输出）需要同目录 lunar.bitmap，随包安装到 share/lunar/
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class LunarConan(ConanFile):
    name = "lunar"
    version = "2.2"
    description = ("Chinese Lunar Calendar conversion utility: solar <-> lunar, "
                   "ganzhi, shengxiao, bazi")
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/lunar"
    topics = ("calendar", "chinese-calendar", "lunar-calendar", "ganzhi",
              "shengxiao", "cli", "conversion")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 直驱 clang（conan 2.x self.run() 默认 cwd = source_folder）
        # -w: lunar.c 是 K&R 风格 + 大量未使用变量，上游本身不干净，避免 -Werror 类噪声
        # -std=gnu99: 保留 GNU 扩展（K&R 定义与 gnu99 兼容）
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "")
        self.run(f"{cc} {cflags} -O2 -w -std=gnu99 -o lunar lunar.c")

    def package(self):
        copy(self, "lunar", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "lunar.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "lunar.bitmap", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "lunar"))
        copy(self, "lunar.c", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "lunar"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
