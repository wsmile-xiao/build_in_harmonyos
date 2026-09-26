#!/usr/bin/env python3
"""Conan recipe for zlib 1.3.2 — 静态库 + -fPIC（鸿蒙 PC，os=OHOS arch=armv8）。

系统同名库（R26/E541）：OHOS SDK sysroot 自带 /usr/lib/aarch64-linux-ohos/libz.so，
本包编译为静态库 libz.a（不发布竞争性 libz.so，不污染系统 /lib/libz.so*）。
因下游会把 zlib 静态链进共享库（cairo/libpng/qpdf/Python 扩展等），
静态库必须用 -fPIC 编译（E539/E541 探针验证：非 PIC libz.a 链进 DSO 报
R_AARCH64_ADR_PREL_PG_HI21 relocation，实测见 logs/pic-probe-nopic-fail.log）。

R33：编译器从 Conan conf tools.build:compiler_executables 获取，禁止裸用 shell 环境变量。
R51：上游官方测试 make check（--static 下 = teststatic + test64）内置于 build()，
     teststatic + test64 实际运行并全部通过（见 logs/make-check.log）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ZlibConan(ConanFile):
    name = "zlib"
    version = "1.3.2.1"
    description = "Massively-used data compression library (DEFLATE/inflate)."
    license = "Zlib"
    homepage = "https://zlib.net/"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."  # zlib 在源码树内构建（configure 生成 Makefile）

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器从 Conan conf 获取（profile [conf] tools.build:compiler_executables），
        # 禁止裸用 ${CC} 等 shell 环境变量。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # CONFIG_SHELL 取 Conan 环境（profile [buildenv]），默认 /data/service/hnp/bin/bash
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # R26/E541: --static + CFLAGS=-fPIC → 静态 libz.a 但对象是 PIC，可被下游链进共享库。
        self.run(f'CONFIG_SHELL={config_shell} CC="{cc}" CFLAGS="-fPIC -O2" {config_shell} ./configure --static --prefix=/')
        # R9: make -j1
        self.run("make -j1")
        # R51: 上游官方测试套件（make check = teststatic + test64，实测全部通过）
        self.run("make check")

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["z"]
        self.cpp_info.set_property("pkg_config_name", "zlib")
        self.cpp_info.set_property("cmake_file_name", "ZLIB")
        self.cpp_info.set_property("cmake_target_name", "ZLIB::ZLIB")
