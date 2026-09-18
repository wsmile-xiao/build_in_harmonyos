#!/usr/bin/env python3
"""Conan recipe for liblzxcomp 20050705 (raw Makefile, no configure).

The upstream Makefile's `all` target builds only the static library
liblzxcomp.a (lzx_layer_nonslide.o + lz_nonslide.o, ar + ranlib). There is
no `install` target, so package() copies the public headers and .a directly.

Head note: liblzxcomp is stored as liblzxcomp.a but the object archive name
is lzxcomp, hence -llzxcomp in cpp_info.libs.

Packaged headers: lzx_compress.h + lzx_constants.h (consumer API) and
lzx_config.h (byte-order config needed by the upstream lzx_test.c harness
and fixed by patches/0003-lzx_config.h.patch).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LiblzxcompConan(ConanFile):
    name = "liblzxcomp"
    version = "20050705"
    description = "LZX compression library (LZX compression/decompression for CHM/DOS/Win3.x format)"
    license = "LGPL-2.1"
    homepage = "https://www.russotto.net/chm/lzx.html"
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
        # tarball 条目带 "./" 前缀，strip_root 可能不生效，显式拍平为根目录
        sub = os.path.join(self.source_folder, "lzx_compress")
        if os.path.isdir(sub):
            for name in os.listdir(sub):
                os.rename(os.path.join(sub, name), os.path.join(self.source_folder, name))
            os.rmdir(sub)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler/archiver come from Conan conf, never shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")
        # R9: always -j1; Makefile has no install target, upstream `all` = static lib only
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1", cwd=self.source_folder, env="conanbuild")

        if self.options.shared:
            self.output.warning("upstream Makefile only builds a static archive; producing static liblzxcomp.a")

    def package(self):
        copy(self, "lzx_compress.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "lzx_constants.h", self.source_folder, os.path.join(self.package_folder, "include"))
        # lzx_config.h 随包发布：上游自测程序 lzx_test.c 依赖它取字节序宏，
        # 且本适配的 0003 补丁正是修正该头文件的大端探测逻辑。
        copy(self, "lzx_config.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "liblzxcomp.a", self.source_folder, os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["lzxcomp"]
        self.cpp_info.system_libs = ["m"]