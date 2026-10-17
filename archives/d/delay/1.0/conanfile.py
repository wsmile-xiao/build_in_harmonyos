#!/usr/bin/env python3
"""Conan recipe — delay 1.0 (upstream plain Makefile build).

版本说明: 上游 rom1v/delay 无 release/tag，Debian 将其打包为 1.0；
积分赛任务版本字段为 "1"。Conan 版本正则要求版本至少 2 个字符
（refs.py: ^[a-z0-9_][a-z0-9_+.-]{1,100}$，单字符 "1" 会报
Invalid package version），故包版本采用合法的 "1.0"，任务分支对应为
feat/delay-1.0（同 disktype 9→9.0 先例；R40: 分支名以 包名-版本号 结尾）。

delay 是一个极简 C 命令行工具：在 stdin 与 stdout 之间引入恒定延时
（`command_A | delay 5s | command_B`），数据先缓存在环形缓冲
（dtbuf），到时间后再写出。纯 C 标准库 + POSIX（poll/gettimeofday），
无外部依赖。

HarmonyOS 适配要点:
  - 上游 Makefile 为普通 make（非 autotools），in-source 构建，
    编译器从 Conan conf（tools.build:compiler_executables）读取（R33），
    不依赖未定义的 shell 环境变量。
  - 上游 `make install` 写死 $(DESTDIR)/usr/bin，package() 直接
    copy 构建产物到 bin/（同 desproxy 处理方式）。
  - 无平台特定代码，无需源码 patch。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class DelayConan(ConanFile):
    name = "delay"
    version = "1.0"
    description = "Constant delay generator: introduce a constant delay between stdin and stdout"
    license = "MIT"
    homepage = "https://github.com/rom1v/delay"
    url = "https://github.com/rom1v/delay"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 纯 C + libc/POSIX，无外部依赖
        pass

    def layout(self):
        basic_layout(self)
        # 上游 Makefile 无 VPATH，必须 in-source 构建
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("delay requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        # R33: 编译器从 Conan conf 获取，禁止裸用 ${CC}
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # 上游默认目标 release 构建 ./delay（main.o + dtbuf.o + time_ms.o）
        self.run("make -j1 CC={}".format(cc))

    def package(self):
        # 上游 make install 写死 $(DESTDIR)/usr/bin，手动 copy 到 bin/
        copy(self, "delay",
             self.build_folder,
             os.path.join(self.package_folder, "bin"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
