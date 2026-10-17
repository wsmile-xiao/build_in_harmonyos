#!/usr/bin/env python3
"""Conan recipe for levenshtein.c 2.0.2.

levenshtein.c 上游只提供纯 GNU Makefile（无 configure 脚本），且 Makefile
只构建 test/example 可执行文件，不构建库目标。本库是单文件实现
(levenshtein.c + levenshtein.h)，因此配方直接编译静态库
liblevenshtein.a 并安装头文件，不经过 AutotoolsToolchain（参考 E097：
纯 Makefile 库的 conan 配方需自定义 make 直构建）。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LevenshteinCConan(ConanFile):
    name = "levenshtein.c"
    version = "2.0.2"
    description = "Levenshtein algorithm (edit distance) in C. Returns a size_t depicting the difference between two strings."
    license = "MIT"
    homepage = "https://github.com/wooorm/levenshtein.c"
    url = "https://github.com/wooorm/levenshtein.c"

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
        # 纯 Makefile 库：上游无 configure，Makefile 也不产库目标。
        # 直接编译 levenshtein.c 为静态库（R33：编译器经 profile buildenv
        # PATH 提供，不裸用 shell 环境变量；工具名直写与 libcrc 配方同款）。
        cc = "clang"
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"
        build_dir = self.build_folder
        src = self.source_folder
        self.run(f"{cc} -std=c99 -O2 -fPIC -c {src}/levenshtein.c -o {build_dir}/levenshtein.o",
                 cwd=build_dir)
        self.run(f"{ar} rcs {build_dir}/liblevenshtein.a {build_dir}/levenshtein.o",
                 cwd=build_dir)
        self.run(f"{ranlib} {build_dir}/liblevenshtein.a", cwd=build_dir)

    def package(self):
        copy(self, "liblevenshtein.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "levenshtein.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["levenshtein"]
