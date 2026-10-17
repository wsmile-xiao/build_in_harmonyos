#!/usr/bin/env python3
"""Conan recipe for zlib 1.3.2 — 静态库 + -fPIC（鸿蒙 PC）。

区别于远端 zlib：远端 `./configure --static` 不加 -fPIC，libz.a 非 PIC，
链进共享库（如 libcairo.so）会报 R_AARCH64 relocation。这里 CFLAGS=-fPIC 编，
静态 libz.a 的对象可被共享库吸收，且不引入运行期 libz.so（不污染系统 /lib/libz.so*）。

消费者：qpdf/cairo 等把 zlib 静态链进 .so 的库，须 require zlib/1.3.2（或 1.3.1.1）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ZlibConan(ConanFile):
    name = "zlib"
    version = "1.3.2"
    description = "Massively-used data compression library (DEFLATE/inflate)."
    license = "Zlib"
    homepage = "https://zlib.net/"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."  # zlib 在源码树内构建（configure 生成 Makefile）

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器从 Conan conf 获取，禁止裸用 shell 环境变量。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # --static + CFLAGS=-fPIC → 静态 libz.a 但对象是 PIC，可链进共享库。
        self.run(f'CONFIG_SHELL={config_shell} CC="{cc}" CFLAGS="-fPIC -O2" {config_shell} ./configure --static --prefix=/')
        # R9: make -j1
        self.run("make -j1")
        # 上游官方测试套件（make check = teststatic + test64）
        self.run("make check")

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["z"]
        self.cpp_info.set_property("pkg_config_name", "zlib")
        self.cpp_info.set_property("cmake_file_name", "ZLIB")
        self.cpp_info.set_property("cmake_target_name", "ZLIB::ZLIB")
