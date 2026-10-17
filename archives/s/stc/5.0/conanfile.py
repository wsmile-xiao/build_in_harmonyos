#!/usr/bin/env python3
"""Conan recipe for STC (Smart Template Containers for C) 5.0.

上游: https://github.com/stclib/STC（官方 tag v5.0）
构建: 纯 Makefile（无 configure）。STC 是 C11 头文件容器库，外加少量 src/*.c
编译为静态归档 libstc.a（cstr_io/cstr_utf8/cregex/fmt/random/cspan/...）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class StcConan(ConanFile):
    name = "stc"
    version = "5.0"
    description = "STC - Smart Template Containers for C (algorithm/cstr/deque/hmap/list/vec/cregex/...)"
    license = "MIT"
    homepage = "https://github.com/stclib/STC"
    url = ""  # CI fills this

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
        # R33: 编译器从 conan conf 获取，不裸用 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # 上游 Makefile 用 `CFLAGS ?=`：环境里若已存在 CFLAGS 会顶掉默认值，
        # 导致 -Iinclude 丢失（本机实测根因），因此显式传完整 CFLAGS。
        # -fPIC 保证静态库可被链入共享对象；-Werror 为上游默认档位。
        cflags = ("-std=c11 -Iinclude -MMD -O3 -Wpedantic -Wall -Wextra "
                  "-Werror -Wno-missing-field-initializers -fPIC")
        # BUILDDIR 固定为 bld，避免上游默认 bld_$(uname)/$(CC) 跨机器不可复现
        self.run(f"make lib CC={cc} CFLAGS='{cflags}' BUILDDIR=bld",
                 cwd=self.source_folder)

    def package(self):
        copy(self, "*",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libstc.a",
             src=os.path.join(self.source_folder, "bld"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["stc"]
        # 静态库引用 libm 符号（fmt/random/cspan）
        self.cpp_info.system_libs = ["m"]
