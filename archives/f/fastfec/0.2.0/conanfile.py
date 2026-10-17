#!/usr/bin/env python3
"""Conan recipe — fastfec 0.2.0 (custom clang build, pure C + vendored PCRE).

上游使用 Zig (build.zig) 构建，但 zig 0.15.2 的 Build API 有 breaking change。
源码为纯 C，直接用 clang 逐文件编译 libfastfec (静态库) + fastfec (CLI 可执行)。
PCRE vendored in src/pcre/，无外部依赖。

R32: settings.os 判断用 in ("Linux", "OHOS")
R33: 编译器从 Conan conf 获取，不裸用 ${CC}
R38: 产物含可执行文件 → 软件级 commands.json 已创建
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FastfecConan(ConanFile):
    name = "fastfec"
    version = "0.2.0"
    description = "FastFEC — a fast FEC filing parser that converts to CSV"
    license = "MIT"
    homepage = "https://github.com/washingtonpost/FastFEC"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 无外部依赖，PCRE vendored
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器从 Conan conf 获取，不裸用 ${CC}
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")

        cflags = "-std=gnu99 -pedantic -Wall -W -Wno-missing-field-initializers -fPIC"
        pcre_cflags = "-DHAVE_CONFIG_H"
        src_dir = self.source_folder
        include_flags = f"-I{src_dir}/src -I{src_dir}/src/pcre"

        # lib 源码 (来自 build.zig libSources)
        lib_sources = [
            "buffer.c", "memory.c", "encoding.c",
            "csv.c", "writer.c", "fec.c",
        ]

        # PCRE vendored 源码 (来自 build.zig pcreSources)
        pcre_sources = [
            "pcre_chartables.c", "pcre_byte_order.c",
            "pcre_compile.c", "pcre_config.c",
            "pcre_dfa_exec.c", "pcre_exec.c",
            "pcre_fullinfo.c", "pcre_get.c",
            "pcre_globals.c", "pcre_jit_compile.c",
            "pcre_maketables.c", "pcre_newline.c",
            "pcre_ord2utf8.c", "pcre_refcount.c",
            "pcre_string_utils.c", "pcre_study.c",
            "pcre_tables.c", "pcre_ucd.c",
            "pcre_valid_utf8.c", "pcre_version.c",
            "pcre_xclass.c",
        ]

        # CLI 源码 (来自 build.zig)
        cli_sources = ["cli.c", "main.c"]

        all_sources = lib_sources + pcre_sources
        obj_files = []

        # 编译 lib 源码
        for src in lib_sources:
            obj = os.path.join(self.build_folder, f"lib_{src.replace('.c', '.o')}")
            obj_files.append(obj)
            src_path = os.path.join(src_dir, "src", src)
            self.run(f'{cc} {cflags} {pcre_cflags} {include_flags} -c "{src_path}" -o "{obj}"')

        # 编译 PCRE 源码
        for src in pcre_sources:
            obj = os.path.join(self.build_folder, f"pcre_{src.replace('.c', '.o')}")
            obj_files.append(obj)
            src_path = os.path.join(src_dir, "src", "pcre", src)
            self.run(f'{cc} {cflags} {pcre_cflags} {include_flags} -c "{src_path}" -o "{obj}"')

        # 静态库
        lib_path = os.path.join(self.build_folder, "libfastfec.a")
        self.run(f'{ar} rcs "{lib_path}" {" ".join(obj_files)}')

        # 共享库 (如果 shared=True)
        if self.options.shared:
            so_path = os.path.join(self.build_folder, "libfastfec.so")
            self.run(f'{cc} -shared -o "{so_path}" {" ".join(obj_files)} -lm')

        # CLI 可执行
        cli_objs = []
        for src in cli_sources:
            obj = os.path.join(self.build_folder, f"cli_{src.replace('.c', '.o')}")
            cli_objs.append(obj)
            src_path = os.path.join(src_dir, "src", src)
            self.run(f'{cc} {cflags} {pcre_cflags} {include_flags} -c "{src_path}" -o "{obj}"')

        # 链接 CLI — 静态库方式
        exe_path = os.path.join(self.build_folder, "fastfec")
        self.run(f'{cc} {cflags} -o "{exe_path}" {" ".join(cli_objs)} -L{self.build_folder} -lfastfec -lm')

    def package(self):
        # 可执行文件
        copy(self, "fastfec", self.build_folder, os.path.join(self.package_folder, "bin"))
        # 静态库
        copy(self, "libfastfec.a", self.build_folder, os.path.join(self.package_folder, "lib"))
        # 共享库 (如果存在)
        copy(self, "libfastfec.so", self.build_folder, os.path.join(self.package_folder, "lib"))
        # 公共头文件
        for h in ["buffer.h", "memory.h", "encoding.h", "csv.h", "writer.h",
                   "fec.h", "export.h", "compat.h", "mappings.h", "mappings_generated.h",
                   "cli.h"]:
            copy(self, h, os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["fastfec"]
        self.cpp_info.bindirs = ["bin"]  # R38/L0k: 声明可执行目录
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
