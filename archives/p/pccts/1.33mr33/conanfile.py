#!/usr/bin/env python3
"""Conan recipe — PCCTS 1.33MR33 (Purdue Compiler Construction Tool Set).

PCCTS 是 ANTLR 1.x 的宿主工具集，**上游不是单构建根**：根 makefile 的默认目标
只是依次 `cd` 进各子目录调 `$(MAKE)`，且每个子目录的 makefile 各自带 `CC=cc`、
`COPT=-O` 硬编码默认值，没有 configure、没有 install 目标。因此本配方自写
build/package 步骤，按真实依赖顺序显式驱动：

    bin/ 必须先于 sorcerer
      ├─ antlr        → bin/antlr   （sorcerer 生成 sor.c/parser.dlg 要用它）
      ├─ dlg          → bin/dlg     （同上，生成 scan.c）
      ├─ sorcerer     → bin/sor     （依赖 bin/antlr + bin/dlg，故排第三）
      │    └─ sorcerer/lib          （sor 的运行期 AST/栈支持对象）
      └─ support/genmk → genmk      （独立，无依赖，最后 mv 进 bin/）

新 libc++ / clang 15 下的两处硬伤（编译探针实测定性）：

1. ``sorcerer/lib/{sorlist,sintstack}.c`` 头部只有 <stdio.h>/<setjmp.h>，
   **缺 #include "pcctscfg.h"** ⇒ 其中 ``#ifdef __STDC__ → #define
   PCCTS_USE_STDARG`` 那段不生效 ⇒ 掉进 ``#else <varargs.h>`` 分支 ⇒
   clang 15 的 varargs.h shim 直接 ``#error "Please use <stdarg.h>"``。
   同目录 astlib.c/sstack.c 因带了 pcctscfg.h 而编译通过，可作对照。
   ⇒ 配方层 ``COPT`` 注入 ``-DPCCTS_USE_STDARG`` 即等价修复，**零源码补丁**
   （pcctscfg.h 对 __STDC__/__USE_PROTOS/__cplusplus 三个条件都定义该宏，
   注入只是把这份本就该生效的配置提前到命令行）。

2. ``h/pccts_iostream.h`` 的 ``#else <iostream.h>`` 分支同样因
   PCCTS_USE_NAMESPACE_STD 未定义而命中老式头 ⇒ 主产物是纯 C 不受影响，
   但 C++ 侧（test_package 与上游 testcpp）必须带上该宏。

安装面按 Debian ``debian/install`` 权威参照：4 个可执行 + ``h/*.[hc]``/``h/*.cpp``
+ ``sorcerer/h/*.h`` + sorcerer/lib 的两个支持源文件；**上游不产出 .a/.so**
（sorcerer/lib 只编 .o 不归档），故无 libs，package_type 走 application 语义。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.tools.layout import basic_layout


class PcctsConan(ConanFile):
    name = "pccts"
    version = "1.33mr33"
    description = "Purdue Compiler Construction Tool Set (PCCTS) — ANTLR 1.x, DLG and Sorcerer"
    license = "public-domain"
    homepage = "http://www.polhode.com/pccts.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # 构建：自写步骤，显式表达子目录依赖顺序（任务卡风险 1）
    # ------------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器一律取自 Conan conf，不读 shell 环境（CI worker 上 ${CC} 为空）。
        # 注意 conf 是**单个 dict**（键 c/cpp/...），不支持 ":c" 子键写法 ——
        # 本机 conan 2.29.1 对不存在的子键直接抛 ConanException（G2 实测）。
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = comp_execs.get("c") or "clang"
        cxx = comp_execs.get("cpp") or "clang++"

        # COPT 承载优化；它被四个子目录 makefile 全部引用进 CFLAGS，是唯一能一次覆盖到
        # sorcerer/lib 的注入点。（该两文件的 varargs 根因已由补丁 0001/0002 补 pcctscfg.h
        # 根治，此处不再依赖 -DPCCTS_USE_STDARG —— 探针 J 实测带补丁无宏即 0 error。）
        copt = "-O2"

        src = self.source_folder
        bindir = os.path.join(src, "bin")
        os.makedirs(bindir, exist_ok=True)

        # ① bin/antlr —— 后两步的生成器，必须最先
        self.run(f"make -C antlr CC={cc} COPT='{copt}' -j1", cwd=src)
        # ② bin/dlg —— sorcerer 与 antlr 自身生成 scan.c 都需要
        self.run(f"make -C dlg CC={cc} COPT='{copt}' -j1", cwd=src)
        # ③ sorcerer（其 makefile 的 all 目标先编 sor 再递归 sorcerer/lib）
        self.run(f"make -C sorcerer CC={cc} COPT='{copt}' CXX={cxx} -j1", cwd=src)
        # ④ support/genmk —— 独立，无上游依赖
        self.run(f"make -C support/genmk CC={cc} COPT='{copt}' -j1", cwd=src)
        # 上游不把 genmk 放进 bin/（根 makefile 用 mv 完成），这里补齐
        self.run("mv -f support/genmk/genmk bin/genmk", cwd=src)

    # ------------------------------------------------------------------
    # 安装：上游无 install 目标，按 Debian debian/install 口径手工落盘
    # ------------------------------------------------------------------
    def package(self):
        src = self.source_folder
        dst = self.package_folder

        # ① 四个可执行 → bin/
        #    注：conan.tools.files.copy 的形参是 src=/dst=（不是 src_path=/dst_path=，
        #    后者会 TypeError，G2 实测），与仓库内全部先例一致。
        for exe in ("antlr", "dlg", "sor", "genmk"):
            copy(self, exe,
                 src=os.path.join(src, "bin"),
                 dst=os.path.join(dst, "bin"))

        # ② PCCTS 运行期头（生成出来的 parser 需要 include 它们）→ include/
        #    只取 .h/.c/.cpp，排除 .dsp/.dsw/.bat 这类 IDE 工程残留
        for ext in ("*.h", "*.c", "*.cpp"):
            copy(self, ext,
                 src=os.path.join(src, "h"),
                 dst=os.path.join(dst, "include"))

        # ③ Sorcerer 头 → include/sorcerer/
        copy(self, "*.h",
             src=os.path.join(src, "sorcerer", "h"),
             dst=os.path.join(dst, "include", "sorcerer"))

        # ④ Sorcerer 运行期支持源（STreeParser/errsupport 由消费者按需编译）
        for f in ("errsupport.c", "STreeParser.cpp"):
            copy(self, f,
                 src=os.path.join(src, "sorcerer", "lib"),
                 dst=os.path.join(dst, "include", "sorcerer"))

        # 保持包面干净：仅当这些目录真的存在时才删（本包只产 bin/include，
        # 直接 rmdir 会对不存在路径抛 FileNotFoundError）
        for sub in (("lib", "cmake"), ("share",), ("lib", "pkgconfig")):
            p = os.path.join(dst, *sub)
            if os.path.isdir(p):
                rmdir(self, p)

    def package_info(self):
        self.cpp_info.includedirs = ["include", "include/sorcerer"]
        self.cpp_info.bindirs = ["bin"]
        # 上游不产出库文件（sorcerer/lib 仅编 .o），故无 libs
        self.cpp_info.libs = []

        # 生成器式工具，按工具名暴露，方便 test_package 与下游复用
        self.cpp_info.set_property("cmake_file_name", "pccts")
        self.cpp_info.set_property("cmake_target_name", "pccts::pccts")
