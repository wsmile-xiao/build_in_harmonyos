#!/usr/bin/env python3
"""Conan recipe — saint 2.5.0 (Makefile, 5 个命令行工具)

SAINT (Significance Analysis of INTeractome) 是一组分析 AP-MS（亲和纯化质谱）
数据的 C 命令行工具。源码为纯 Makefile 工程，无 configure，输出 5 个可执行：
saint-reformat / saint-spc-noctrl / saint-spc-noctrl-matrix / saint-spc-ctrl / saint-int-ctrl。
硬依赖 GSL（gsl_rng 采样 MCMC），Makefile 固定链接 -lm -lgsl -lgslcblas。

本配方按 R33 从 Conan conf 取编译器路径、从 gsl 依赖取 -I/-L，统一通过
make 命令行变量覆盖 Makefile 默认的 CC/CFLAGS/LIBS（命令行变量优先于 Makefile 内赋值）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class SaintConan(ConanFile):
    name = "saint"
    version = "2.5.0"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    license = "GPL-3.0-or-later"
    homepage = "http://saint-apms.sourceforge.net/Main.html"
    url = "https://sourceforge.net/projects/saint-apms/"
    description = "Significance Analysis of INTeractome (SAINT) — AP-MS interactome data analysis tools"

    def validate(self):
        # R32：平台分支显式评估 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"saint is only supported on Linux/OHOS, not {self.settings.os}")

    def requirements(self):
        # saint 的 Makefile 固定 -lgsl -lgslcblas -lm。作为 requires 把 gsl 的
        # 头文件与共享库（libgsl.so/libgslcblas.so）带入构建与运行闭包。
        self.requires("gsl/2.8")

    def layout(self):
        # Makefile 用 $(shell pwd) 作为 TOPDIR，必须在源码根执行 make。
        # 采用本仓库 makefile 工程通用手法：basic_layout + build 置 "."（in-source）。
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        # 归档为 zip，含两个顶层条目：源码目录 SAINT_v2.5.0/ 与垃圾目录 __MACOSX/。
        # 多根目录下 conan 的 strip_root 行为不确定，故 strip_root=False 后在此显式处理：
        #   1) 剔除 __MACOSX/ 与预编译 bin/；2) 若源码仍包在 SAINT_v2.5.0/ 内则提升到根。
        import shutil
        get(self, **self.conan_data["sources"], strip_root=False)
        srcroot = self.source_folder
        for junk in ("__MACOSX",):
            p = os.path.join(srcroot, junk)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
        nested = os.path.join(srcroot, "SAINT_v2.5.0")
        if os.path.isdir(nested):
            for entry in os.listdir(nested):
                s = os.path.join(nested, entry)
                d = os.path.join(srcroot, entry)
                if os.path.isdir(s) and not os.path.exists(d):
                    shutil.move(s, d)
                elif os.path.isfile(s):
                    shutil.move(s, d)
            shutil.rmtree(nested, ignore_errors=True)
        prebuilt = os.path.join(srcroot, "bin")
        if os.path.isdir(prebuilt):
            shutil.rmtree(prebuilt, ignore_errors=True)

    def _compiler(self):
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c")
        return cc or "/data/service/hnp/bin/clang"

    def _gsl_flags(self):
        gsl = self.dependencies["gsl"]
        inc = " ".join("-I" + p for p in gsl.cpp_info.includedirs)
        lib = " ".join("-L" + p for p in gsl.cpp_info.libdirs)
        return inc, lib

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler()
        inc, lib = self._gsl_flags()
        # R33：编译器/路径全部来自 Conan 环境，不依赖 shell 裸变量。
        # CFLAGS 注入 gsl 头文件路径（Makefile 编译 -c 时不带 -I 到 gsl）；
        # LIBS 注入 gsl 库路径并保留上游 -lgsl -lgslcblas -lm 闭包。
        # R39：-fcommon（上游 saint.h 对 burn/iter/freq/freqgroup/modelvar/NORMALIZE
        # 等全局变量一律按"无 extern 的 tentative definition"声明，且所有 .c 都
        # #include saint.h、各自独立 -c 成 .o）。gcc 默认 -fcommon 会在链接期把同名
        # tentative 定义合并为 common symbol，故上游 gcc 构建正常；而 clang 从 15 起
        # 默认 -fno-common，每个 .o 都变成 .bss 的强定义，链接报 duplicate symbol:
        # burn/iter/freq/...。加 -fcommon 让 clang 恢复与 gcc 一致的 common 语义，
        # 同名全局变量合并，真机即可正常链接（本机最小复现已验证）。
        cflags = inc + " -O2 -fcommon"
        libs = lib + " -lgsl -lgslcblas -lm"
        # 逐目标构建（而非 `make all`）：all 末尾触发 clean 的 `rm src/*/*.gch`，
        # 在无 .gch 产物时 glob 不匹配会导致 make 失败；单个 target 自包含编译+链接。
        # R9：-j1 单作业（HMDFS 上并行 make 会撞 jobserver fifo）。
        # R38：单个工具 target 直接 `mv *.o $(BUILD)`，而 build/ 目录只由 makeDirs
        # 目标创建（all 的前置）。逐目标构建不经过 all，故必须先跑一次 makeDirs，
        # 否则 `mv *.o build` 会报 "build not directory"（真机实测错误）。
        self.run('make -j1 makeDirs CC="{cc}" CFLAGS="{cflags}" LIBS="{libs}"'.format(
            cc=cc, cflags=cflags, libs=libs))
        tools = [
            "saint-reformat",
            "saint-spc-noctrl-matrix",
            "saint-spc-noctrl",
            "saint-spc-ctrl",
            "saint-int-ctrl",
        ]
        self.run('make -j1 {tools} CC="{cc}" CFLAGS="{cflags}" LIBS="{libs}"'.format(
            tools=" ".join(tools), cc=cc, cflags=cflags, libs=libs))

    def package(self):
        bindir = os.path.join(self.build_folder, "bin")
        for tool in ("saint-reformat", "saint-spc-noctrl", "saint-spc-noctrl-matrix",
                     "saint-spc-ctrl", "saint-int-ctrl"):
            copy(self, tool, src=bindir, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # application：只暴露 bin/，供运行闭包使用。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
