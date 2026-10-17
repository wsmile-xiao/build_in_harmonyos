#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for snooze 0.5 — run a command at a particular time.

snooze 是 Tobias Waldekranz 的"定时执行命令"工具（public domain / 见上游
README），设计目标是配合 runit 之类的**服务监督系统**替代 cron：

- 助记式时间语法：`-H 22`（22 点）、`-w 1-5`（周一到周五）、`-M 1,3,5`
  （第 1/3/5 分钟）、`-d 1`（每月 1 号）、`-D 1,100,200`（年积日）、
  `-W 1-53`（ISO 周）、`-m 1-12`（月）、`-S`（秒）
- 支持范围/列表两种模式写法
- 相对 cron 的独有特性：不可能出现重叠运行（由监督系统保证）、可按 ISO 周与
  年积日过滤、无需中心守护进程、可被立即强制触发、可自定义日志、
  对系统时间跳变鲁棒、可用时间戳文件保证两次运行间的最小等待、随机延迟、
  可变 slack（因而不需要 anacron）、可临时从命令行直接运行

OHOS 适配 (aarch64 musl):
- 单 .c 文件（snooze.c ~8.6KB），零外部依赖
  （仅 libc：sys/stat、sys/types、ctype、errno、signal、stdio、stdlib、
   string、time、unistd、sys/auxv）
- 上游 Makefile 的 `install` 目标用 `mkdir -p` / `install -m0755`，
  在交叉编译环境不需要（本包只做 build/package），故 build() 直驱 clang
- 产出单可执行文件 bin/snooze
- ★ 干跑模式 `-n` 只打印"接下来 5 次会运行的时刻"并退出，不进入等待；
  这使本包可以在 CI 上做**完全时间无关**的行为验证
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class SnoozeConan(ConanFile):
    name = "snooze"
    version = "0.5"
    description = ("Run a command at a particular time: mnemonic time patterns, "
                   "ISO week / day-of-year filters, supervision-friendly cron replacement")
    license = "MIT"
    homepage = "https://github.com/chneukirchen/snooze"
    topics = ("cron", "scheduler", "runit", "supervision", "time", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 直驱 clang（conan 2.x self.run() 默认 cwd = source_folder）
        # 上游 Makefile 只有 all / clean / install，install 依赖 mkdir+install，
        # 交叉编译环境不需要；build() 只编译二进制。
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "")
        self.run(f"{cc} {cflags} -O2 -w -std=gnu99 -o snooze snooze.c")

    def package(self):
        copy(self, "snooze", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "snooze.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "snooze"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
