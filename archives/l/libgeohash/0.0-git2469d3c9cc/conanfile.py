#!/usr/bin/env python3
"""Conan recipe — libgeohash (Makefile project, static library).

libgeohash 是一个纯 C 静态库（无 configure 脚本，Makefile 直接 gcc/ar）。
适配要点：
  - 构建系统为原始 Makefile，无 ./configure，build() 直接 make -j1。
  - 编译器/归档工具从 Conan conf 获取（R33：禁止裸用 ${CC}/${CFLAGS}）。
  - R9: 始终 -j1。
  - package() 收集 geohash.h 与 libgeohash.a。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibgeohashConan(ConanFile):
    name = "libgeohash"
    version = "0.0-git2469d3c9cc"
    description = "A static C library for encoding/decoding geohashes (SimpleGeo)."
    license = "MIT"
    homepage = "https://github.com/simplegeo/libgeohash"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器/归档工具从 Conan conf 获取，绝不裸用 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar") or "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") or "llvm-ranlib"

        # 原始 Makefile：gcc -c geohash.c && ar rcs libgeohash.a
        # 平台适配补丁已把 Makefile 的 gcc 替换为可注入的 $(CC)/$(AR)/$(RANLIB)
        # basic_layout 下构建目录与源码目录分离，make 必须在 source_folder 中执行
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "geohash.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "libgeohash.a", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["geohash"]
