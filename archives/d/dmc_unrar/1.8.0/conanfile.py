#!/usr/bin/env python3
"""Conan recipe — dmc_unrar 1.8.0（stb 风格单文件 C 库，无构建系统）。

dmc_unrar 是 dependency-free 的单文件 RAR 解压库：上游无 configure/make/
CMake，使用方式为直接 #include "dmc_unrar.c"。此处编译出静态库 libdmc_unrar.a，
并同时安装 dmc_unrar.c 与包装头 dmc_unrar.h（DMC_UNRAR_HEADER_FILE_ONLY 声明
模式），消费者可任选以下方式：
  1) #include <dmc_unrar.h>  + 链接 libdmc_unrar.a（声明 + 链接）
  2) #include <dmc_unrar.c>             （上游 stb 风格整体内联）
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, save, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class DmcunrarConan(ConanFile):
    name = "dmc_unrar"
    version = "1.8.0"
    description = "A dependency-free, single-file FLOSS library for unpacking and decompressing RAR archives"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/DrMcCoy/dmc_unrar"
    url = "https://github.com/DrMcCoy/dmc_unrar"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33：编译器取自 profile conf（tools.build:compiler_executables），不依赖 shell 环境变量
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "cc")
        # basic_layout 下 source_folder=build/src，须用绝对路径引用源文件
        src = os.path.join(self.source_folder, "dmc_unrar.c")
        obj = os.path.join(self.build_folder, "dmc_unrar.o")
        cflags = ["-O2", "-c", src, "-o", obj]
        if self.options.shared:
            cflags.insert(1, "-fPIC")
        self.run("%s %s" % (cc, " ".join(cflags)))
        if self.options.shared:
            self.run("%s -shared -o libdmc_unrar.so %s" % (cc, obj))
        else:
            self.run("ar rcs libdmc_unrar.a %s" % obj)

    def package(self):
        copy(self, "libdmc_unrar.*", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "dmc_unrar.c", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # 包装头：DMC_UNRAR_HEADER_FILE_ONLY -> 仅声明；实现由 libdmc_unrar 提供
        wrapper = (
            "#ifndef DMC_UNRAR_H\n"
            "#define DMC_UNRAR_H\n"
            "#ifndef DMC_UNRAR_HEADER_FILE_ONLY\n"
            "#define DMC_UNRAR_HEADER_FILE_ONLY\n"
            "#endif\n"
            "#include \"dmc_unrar.c\"\n"
            "#endif /* DMC_UNRAR_H */\n"
        )
        save(self, os.path.join(self.package_folder, "include", "dmc_unrar.h"), wrapper)

    def package_info(self):
        self.cpp_info.libs = ["dmc_unrar"]