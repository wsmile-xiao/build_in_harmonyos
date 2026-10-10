#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for palbart 2.14 — GNU barcode 的 PostScript 条码驱动。

palbart 是 GNU barcode 2.14 的一个后端驱动：它本身不是生成 PostScript 的
排版器，而是条码描述语言的**解释器 + 编码器**。读入一份纯文本的条码描述
文件（符号表 + 字模定义），边解释边输出两份产物：

  <输入名>.lst   可打印的符号清单：逐行回显输入、给出每行在 .bin 中的
                 字节偏移，末尾汇总诊断（No detected errors / N detected
                 errors）与链接生成情况（No links generated）。
  <输入名>.bin   编码后的条码位流，固定记录头 + 各符号的位段。

描述语言的关键语法（均取自实测，��� notes.md 附完整用例）：
  *4 2 100 50     伪操作：定义字模 4（Code 39），参数为 2/100/50
  $HELLO          以 $ 开头的行是字面文本（literal），不查符号表
  HELLO           不带 $ 的行按符号名查表；未定义则报 UD undefined
  *0 5            伪操作：以码 5 结束当前页

OHOS aarch64 适配要点：
- 源包只有 3 个文件：palbart.c（170KB，4353 行）+ README + palbart.1
  （man page）。无 Makefile / configure / CMakeLists —— 上游把构建放在
  顶层 GNU makefile 里，而 Debian 原包只取源码子集，所以配方直驱 clang。
- **零 patch**：palbart.c 一次 clang-ohos 交叉编译通过，无符号冲突、
  无缺失 API。它只 include ctype/errno/stdio/stdlib/string 五个头文件，
  全部由 OHOS sysroot 自带，产物 ELF64/AArch64 且 NEEDED 仅 libc.so。
- 产出 bin/palbart（可执行文件）+ share/doc/palbart/{README,palbart.1}。
  不安装 gnuplot / ghostscript 等排期工具：解释器阶段是纯用户态、无网络、
  无设备依赖，条码渲染由下游 PostScript 解释器完成。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class PalbartConan(ConanFile):
    name = "palbart"
    version = "2.14"
    description = (
        "GNU barcode 2.14 PostScript driver: interprets a barcode description "
        "language file and emits a printable symbol listing plus the encoded "
        "barcode bitstream"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/barcode/"
    topics = ("barcode", "postscript", "gnu", "codabar", "code39", "interpreter")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml", "CMakeLists.txt"

    def package_id(self):
        # 纯 C 用户态程序，不随 build_type / 编译优化变化
        self.info.settings.build_type = "Any"
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("arch")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        # build_folder="."：让 generators/ 直接落在构建根，CMake(self) 才找得到
        # CMakePresets.json。默认的 build/{build_type} 分层会让辅助函数报
        # "CMakePresets.json was not found in .../build/Release/generators"。
        cmake_layout(self, build_folder=".")

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        # ★ 用 CMakeToolchain 驱动编译，而不是 self.run("<clang-ohos.bat> ...")。
        #   实测（Conan 2.29.1 + Windows）：同样的命令
        #     subprocess.run(f"{cc} --version")  → rc=0
        #     self.run(f"{cc} --version")        → Error 1
        #   Conan 的 self.run 在本机会把 .bat 调用打散（报
        #   "'.' is not recognized as an internal or external command"）；
        #   而 CMakeToolchain 走的是 CMake 自己的编译器调用路径，不受影响，
        #   这也是本仓库其它配方统一的做法。详见 notes.md「坑 2」。
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "palbart", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        for doc in ("README", "palbart.1"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "doc", "palbart"),
                 keep_path=False)

    def package_info(self):
        # 只有一个可执行文件，没有库也没有公开头文件
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
