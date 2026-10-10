#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for lpctools 1.07 — NXP LPC 微控制器的 ISP 烧录工具集。

三个可执行文件：

  lpcprog           串口 ISP 烧录器。命令：dump / flash / id / blank / go
  lpcisp            另一条 LPC 产品线的烧录器，命令集不同
  lpc_binary_check  读取芯片型号并打印 id 信息

OHOS aarch64 适配要点：
- **零 patch**。九个源文件只依赖 libc 的 stdio / stdlib / string / stdint /
  unistd / fcntl / termios / getopt / errno，全部由 OHOS sysroot 自带。
  三个二进制一次 clang-ohos 交叉编译通过，产物 ELF64 / AArch64，
  `NEEDED` 仅 libc.so。
- **必须照搬上游的三组对象集**。check.c 自带 main()，是独立的自检程序；
  与 lpcprog / lpcisp 混链会得到
  `ld.lld: duplicate symbol: main / help / trace_on`。
  上游 Makefile 把对象集拆成三组正是为此。见 CMakeLists.txt。
- 装 bin/{lpcprog,lpcisp,lpc_binary_check} 与
  share/{lpctools/lpctools_parts.def, doc/lpctools/{README,lpcprog.1}}。
  parts.def 是芯片型号描述表，lpcprog 默认从 /etc/lpctools_parts.def 或
  当前目录读取；包内那份供调用方复制或用 `-p` 指定。
- **不安装**任何串口驱动或 udev 规则：设备节点由调用方准备。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class LpctoolsConan(ConanFile):
    name = "lpctools"
    version = "1.07"
    description = (
        "ISP (In-System Programming) toolset for NXP LPC microcontrollers: "
        "lpcprog / lpcisp flashers plus lpc_binary_check"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://sources.debian.org/src/lpctools/1.07/"
    topics = ("embedded", "lpc", "nxp", "isp", "flashing", "serial", "mcu")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml", "CMakeLists.txt"

    def package_id(self):
        # 纯 C 用户态程序，不随 build_type / 编译优化变化
        self.info.settings.build_type = "Any"
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("arch")

    def layout(self):
        cmake_layout(self, build_folder=".")

    def generate(self):
        CMakeToolchain(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 用 CMakeToolchain 驱动编译：本地实测 Conan 2.29.1 的 self.run 在
        # build profile 带 [buildenv] 时会把命令打散（报 "'.' is not recognized
        # as an internal or external command"），CMake 自己的编译器调用路径不受影响。
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        for exe in ("lpcprog", "lpcisp", "lpc_binary_check"):
            copy(self, exe, src=self.build_folder,
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "lpctools_parts.def", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "lpctools"),
             keep_path=False)
        for doc in ("README", "lpcprog.1"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "doc", "lpctools"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
