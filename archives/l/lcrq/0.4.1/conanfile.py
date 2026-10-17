#!/usr/bin/env python3
"""Conan recipe — lcrq 0.4.1（Librecast RaptorQ FEC 库，autotools）。

HarmonyOS 适配要点：
- 纯 C 无外部依赖（configure 仅探测 libc 族函数：clock_gettime/getrandom/arc4random_uniform）。
- aarch64 走 NEON 实现（matrix_neon.o + gf256_simd.o），由上游 src/Makefile.in 按 CPU 分派。
- 上游仅构建共享库 liblcrq.so（SONAME liblcrq.so.0.0，ABIVERS 0.0），无静态目标。
- 上游 Makefile 非 VPATH 感知（src/Makefile.in 的 -I../include 等），必须 in-tree 构建。
- 补丁：config.guess/sub 加 HarmonyOS 三元组识别；顶层 install 去掉 doc/man 页；
  soname 别名由 ln -sf 改 cp -f（真机文件系统符号链接受限，避坑指南 #15）。
- librecast 0.11.2 对本库为硬链接依赖（src/Makefile.in 无条件 LIBS += -llcrq）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LcrqConan(ConanFile):
    name = "lcrq"
    version = "0.4.1"
    description = "RaptorQ (RFC6330) forward error correction library for the Librecast Project"
    license = "GPL-2.0-only OR GPL-3.0-only"
    homepage = "https://librecast.net/lcrq.html"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # 上游只构建共享库（all: $(SOFILE)），不提供静态目标
    options = {"shared": [True]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # 纯 C，无外部依赖

    def layout(self):
        # 上游 Makefile 非 VPATH 感知，必须与上游一致使用 in-tree 构建
        basic_layout(self, src_folder=".", build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS 不允许 execve 脚本（configure 解包后无法直接执行，chmod +x 也不生效），
        # configure 必须 sh 调用；make/configure 产出的 ELF 可正常执行（实测）。
        # 先例：archives/a/autofs/5.1.9（E046）。
        self.run("sh ./configure --prefix=/", env="conanbuild")
        self.run("make -j1", env="conanbuild")
        # ── 上游官方测试（必做）──
        # 20 个独立用例（0000-*: RaptorQ 编解码/参数；0001-*: q 队列），
        # 纯算法无网络依赖；runner 退出码 0=PASS / 1=WARN / >=2=FAIL。
        # 0006 补丁把顶层 test 转发改为 maketest（tar 归档中 test/all 符号链接
        # 在 HMDFS 解包时被跳过，test/all 为空目录会导致 0 用例空转）。
        self.run("make -j1 test", env="conanbuild")

    def package(self):
        self.run("make -j1 install DESTDIR={}".format(self.package_folder), env="conanbuild")
        # 安装产物：lib/liblcrq.so(.0/.0.0)（补丁后均为实体文件）+ include/lcrq.h

    def package_info(self):
        # SONAME 为 liblcrq.so.0.0（ABIVERS 0.0），包内同时提供 .so/.so.0 别名
        self.cpp_info.libs = ["lcrq"]
        self.cpp_info.includedirs = ["include"]
