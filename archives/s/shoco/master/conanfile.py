#!/usr/bin/env python3
"""Conan recipe — shoco master (pure Makefile C99 library + CLI)

shoco 是零依赖 C99 短字符串压缩库（Ed-von-Schleck/shoco）。
上游为纯 Makefile 项目：无 configure、无 make install 目标，
构建产出 shoco.o（库）+ shoco（CLI，shoco-bin.c）+ tests/test_input（测试）。

OHOS 适配要点（本地 W3 实测验证）：
1. 纯 Makefile：不走 autotools，直接 CC/AR 调用（编译器由 profile conf 注入）。
2. 上游无 install 目标：package() 手工安装 shoco.h/shoco_model.h/shoco_table.h
   -> include/，libshoco.a -> lib/，shoco CLI -> bin/（R38 声明 commands.json）。
3. 静态库默认（R26 无关——非系统同名库，但上游本身只有静态形态；shared 选项
   保持以符合模板，实际仅静态路径生效）。
4. 编译 flag 从 conf 取编译器可执行，不裸用 ${CC}（R33）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ShocoConan(ConanFile):
    name = "shoco"
    version = "master"
    description = "shoco: a fast compressor for short strings (C99, zero-dependency)"
    license = "MIT"
    homepage = "https://github.com/Ed-von-Schleck/shoco"
    url = "https://github.com/Ed-von-Schleck/shoco"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # 纯 Makefile 就地构建（无 out-of-source 支持）
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("shoco is built for Linux/OHOS only")

    def build(self):
        apply_conandata_patches(self)
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c") or "cc"
        ar = self.conf.get("tools.build:compiler_executables", default={}).get("ar") or "ar"
        cflags = "-std=c99 -O3 -Wall -fPIC"
        self.run(f"{cc} {cflags} -c shoco.c -o shoco.o")
        self.run(f"{ar} rcs libshoco.a shoco.o")
        # CLI（R38：构建产物含可执行文件 -> commands.json 软件级声明）
        self.run(f"{cc} {cflags} shoco.o shoco-bin.c -o shoco")

    def package(self):
        inc = os.path.join(self.package_folder, "include")
        lib = os.path.join(self.package_folder, "lib")
        bin_dir = os.path.join(self.package_folder, "bin")
        for h in ("shoco.h", "shoco_model.h", "shoco_table.h"):
            copy(self, h, src=".", dst=inc)
        copy(self, "libshoco.a", src=".", dst=lib)
        copy(self, "shoco", src=".", dst=bin_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["shoco"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
