#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for prctl 1.7 — query/control process behavior via prctl(2).

prctl 是 Ronny Hegewald / Stephan Mueller 的 `prctl(2)` 命令行封装
（Debian 源包 prctl），用于**查询或控制进程行为**：

- `--unaligned=[silent|signal|default]`  非对齐内存访问的处理策略
- `--fpemu=[silent|signal|default]`      浮点辅助故障的处理策略
- `--mcekill=[early|late|default]`       硬件内存损坏时的线程终止策略
- `-q`                                  查询当前设置
- 后接 `command` 则该命令以此设置 exec

**平台差异（重要）**：`--unaligned` 与 `--fpemu` 是 **ia64 专有**的 prctl 操作。
在 aarch64 上内核返回 EINVAL，prctl 会打印
`ERROR: This platform does not implement set_unaligned prctl feature.` 并退出 1。
`--mcekill` 是架构无关操作（PR_MCE_KILL / PR_MCE_KILL_GET）。本包的消费者测试
把这一差异写成了显式分级判据。

OHOS 适配 (aarch64 musl):
- 单 .c 文件（prctl.c），**无 config.h 依赖**（仅 unistd/stdio/stdlib/getopt/
  errno/pwd/sys/prctl/string），可直接 clang 编译
- 上游是 autotools 工程但 tarball **不含生成的 `configure`**（只有 configure.ac
  与 Makefile.in），交叉编译需要 autoreconf；且 configure.ac 里 AC_INIT 仍是
  模板占位（`AC_INIT([FULL-PACKAGE-NAME], [VERSION], ...)`），
  故 build() 直驱 clang，避开整条 autotools 链路
- 版本串由 `#define VERSION "1.7"` 硬编码在源码里，不依赖 configure
- 产出单可执行文件 bin/prctl
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class PrctlConan(ConanFile):
    name = "prctl"
    version = "1.7"
    description = ("Query or control process behavior via prctl(2): unaligned "
                   "access policy, FP emulation policy, MCE kill policy")
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/prctl"
    topics = ("prctl", "process", "syscall", "mce", "fpemu", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 直驱 clang（conan 2.x self.run() 默认 cwd = source_folder）
        # 不用 autotools：tarball 不含生成的 configure（仅 configure.ac +
        # Makefile.in），需要 autoreconf；且 configure.ac 的 AC_INIT 仍是
        # 模板占位。prctl.c 不依赖 config.h，直接编译即可。
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "")
        self.run(f"{cc} {cflags} -O2 -w -std=gnu99 -o prctl prctl.c")

    def package(self):
        copy(self, "prctl", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "prctl.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
