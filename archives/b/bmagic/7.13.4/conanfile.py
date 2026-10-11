#!/usr/bin/env python3
"""Conan recipe — BitMagic (bmagic) 7.13.4 (header-only)

bm::bvector<> / sparse_vector / str_sparse_vector 等位图与压缩向量容器库。
上游以 header-only C++ 库发布（CMakeLists.txt 中 add_library(bm INTERFACE)，
头文件平铺于 src/，消费侧 #include "bm.h"）。本配方按上游使用惯例将 src/
公共头文件平铺安装到 include/；上游官方测试三套（bmtest/bmtest64/ptest）
在 build() 中以 clang++ 同参完整编译，其中 ptest（tests/test_threads）在包内
完整运行（设备实测 8/8 全绿，时长 2–4 分钟量级）；bmtest/bmtest64 为上游明示
"runs for days" 的天数级压测，设备原生后台全量运行留证，未覆盖范围见
test_package/MANIFEST.yml 与 notes.md。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches


class BmagicConan(ConanFile):
    name = "bmagic"
    version = "7.13.4"
    description = "BitMagic C++ Library: bitmap containers (bvector, sparse_vector, str_sparse_vector), algorithms, serialization and SIMD kernels (header-only)"
    license = "Apache-2.0"
    homepage = "https://github.com/tlk00/BitMagic"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # R32 平台检测：header-only 库理论平台无关，仍按规程做白名单校验。
        # 本配方的 build() 编译命令按 POSIX shell 语义编写，不覆盖 Windows。
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos"):
            raise ConanInvalidConfiguration(
                "bmagic 本适配覆盖 Linux/OHOS/FreeBSD/Macos，当前: {}".format(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # 默认单根布局：源码与构建同目录，build() 的产物隔离到 build-tests/
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # ── 上游官方测试：完整编译（tests/stress, tests/stress64, tests/test_threads）──
        # R33：编译器取自 Conan profile conf（tools.build:compiler_executables，
        # 先取 dict 再索引——Conan 2.29 点分子键访问会抛 ConanException），
        # 不依赖 shell 环境变量。
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = exes.get("cpp", "clang++")
        src = self.source_folder
        # 编译参数复刻上游 platforms/aarch64-linux-gnu.mk GNU_CC 分支：
        #   -D_REENTRANT -D_GNU_SOURCE -std=c++17 -Wall + OPT_FLAGS(-O2 -g0)
        # （-march/-mcpu=native 为上游针对本机的优化提示，包内编译改由
        #   Conan profile 决定目标参数，不引入 -march=native。）
        # OHOS 两处差异（均有设备实测证据，见 notes.md / MANIFEST.yml）：
        #   1. OHOS uname -r = "HongMeng Kernel 1.12.0"（含空格），上游
        #      makefile.in 直接内插 $(shell uname -r) 会生成损坏宏
        #      -D__HarmonyOS_HongMeng Kernel 1_12_0；此处以等价单 token 宏
        #      -D__HarmonyOS_HongMeng__ 定义（该宏上游仅作平台标签）。
        #   2. 上游 aarch64 平台 mk 链接参数含 GNU ld 专有 "-export-dynamic"，
        #      OHOS 默认链接器 lld 解析为 "-e xport-dynamic"，ELF 入口为
        #      0x0，运行即段错误；以 clang/lld 正确处理且语义等价的
        #      "-rdynamic" 替代。
        flags = ("-D_REENTRANT -D_GNU_SOURCE -D__HarmonyOS_HongMeng__ "
                 "-std=c++17 -Wall -O2 -g0")
        self.run("mkdir -p build-tests", cwd=src)
        for out, source in (("bmtest", "tests/stress/t.cpp"),
                            ("bmtest64", "tests/stress64/t64.cpp"),
                            ("ptest", "tests/test_threads/ptest.cpp")):
            self.run('{} -c {} -I "{}/src" "{}" -o "build-tests/{}.o"'.format(
                cxx, flags, src, source, out), cwd=src)
            self.run('{} -o "build-tests/{}" "build-tests/{}.o" -rdynamic -lpthread -ldl -lrt'.format(
                cxx, out, out), cwd=src)

        # ── 上游测试运行（包内可承受的完整运行）──
        # ptest（tests/test_threads，线程池 + 并行稀疏向量算法）：
        # 设备实测 8/8 全部 OK（时长 2–4 分钟量级），纳入包内完整运行；该运行同时证明
        # 三套同参编译/链接（含 -rdynamic 入口修复）的二进制在本平台可执行。
        # bmtest / bmtest64 不在包内运行：默认全量为天数级（上游
        # tests/readme.txt 自述 "runs for days"，设备实测 28+ 分钟仅推进
        # 前 3/60+ 测试组），且二者全部命令行选择器（-h/-ll/-s/-bvb 等）
        # 要么退出码 1（-h 仅打印帮助）要么同样是长跑组，无有界子集。
        # 全量运行与未覆盖范围在设备侧原生留证，申报见 test_package/MANIFEST.yml。
        self.run("./build-tests/ptest", cwd=src)

    def package(self):
        # header-only：头文件按上游使用惯例平铺安装（消费侧 #include "bm.h"），
        # 与上游 CMake INSTALL_INTERFACE（include 根）一致。
        src = self.source_folder
        copy(self, "*.h", src=os.path.join(src, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # 无编译产物 → 单一 package_id
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        # CMakeDeps 产物对齐上游 CMake 目标名：find_package(bmagic) + bmagic::bm
        self.cpp_info.set_property("cmake_file_name", "bmagic")
        self.cpp_info.set_property("cmake_target_name", "bm::bm")
