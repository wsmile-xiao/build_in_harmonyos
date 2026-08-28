#!/usr/bin/env python3
"""Conan recipe — adv-17v35x 5.0.7.0 (Advantech PCIe 多串口驱动：用户态工具 getconfig)

上游包 adv-17v35x 为 Advantech ACOM 系列（EXAR 芯片组）PCIe 多串口卡 Linux 驱动，
源码内含两层构建入口：
  * 顶层 Makefile + adv17v35x.c：Linux 内核驱动模块（需要 KERNEL_SRC 内核头文件树），
    鸿蒙 PC 无内核构建环境，无法构建，本配方不构建该部分；
  * getconfig/Makefile + getconfig.c：纯 C 用户态工具（查询串口 RS232/RS422/RS485 模式），
    仅依赖标准 C 头与 linux/serial.h、asm/ioctls.h（OHOS sysroot 提供），可用 OHOS clang 交叉编译。
本配方按 application 类型构建并安装用户态工具 getconfig。
"""

import os

from conan import ConanFile
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Adv17v35xConan(ConanFile):
    name = "adv-17v35x"
    version = "5.0.7.0"
    description = "Advantech ACOM-series (EXAR chipset) PCIe multiport serial driver — user-space getconfig tool"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/adv-17v35x"
    url = ""

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    def build(self):
        # R33: 编译器从 Conan conf 获取，不使用 ${CC}
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        getconfig_dir = os.path.join(self.source_folder, "getconfig")
        # R9: 串行构建 -j1
        self.run(f"make CC={cc} -j1", cwd=getconfig_dir)

    def package(self):
        copy(self, "getconfig",
             os.path.join(self.source_folder, "getconfig"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "readme", self.source_folder,
             os.path.join(self.package_folder, "share", "doc", "adv-17v35x"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]