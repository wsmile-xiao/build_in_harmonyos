#!/usr/bin/env python3
"""Conan recipe for devio 1.2 — read/write from/to block devices (MTD-friendly).

devio 是 John Bowler 2005 个人项目（MIT License）的 dd-like 块设备
读写工具，专为 mtd character 设备设计（jffs2 烧写、bootloader 备份等
嵌入式场景），支持指定区域读写和数据位置输出。

OHOS 适配 (aarch64 musl):
- 单 .c 文件（devio.c 在 src/ 下）+ autotools 框架，但 devio.c 不依赖
  config.h.in 的 HAVE_* 宏（直接 include <fcntl.h> <unistd.h> 等标准
  POSIX 头），conanfile 跳过 autogen + configure，直接 clang 编译
- 直链 clang 编译（不嵌 cd，conan 2.x self.run() 默认 cwd = source_folder，
  devio.c 在 src/devio.c 相对路径可直接访问）
- 编译产出单可执行文件 bin/devio
- autotools 文件（configure/Makefile.in）随包携带但 build() 不调用，
  保留以便上游开发者重新生成；conan 适配用直驱 clang 保证确定性
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class DevioConan(ConanFile):
    name = "devio"
    version = "1.2"
    description = "dd-like tool for correctly reading/writing regions of block devices (MTD-friendly)"
    license = "MIT"
    homepage = "https://launchpad.net/ubuntu/+source/devio"
    topics = ("block-device", "mtd", "jffs2", "embedded")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 直链 clang 编译（conan 2.x self.run() 默认 cwd=source_folder）
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "") + " -O2 -Wall"
        # devio.c 在 src/ 子目录，conan 2.x cwd 默认 source_folder 根
        self.run(f"{cc} {cflags} -o devio src/devio.c")

    def package(self):
        copy(self, "devio", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "devio"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share", "licenses"]
