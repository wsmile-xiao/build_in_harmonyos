#!/usr/bin/env python3
"""Conan recipe — offbrand-lib 1.0.0 (plain Makefile).

Offbrand is a collection of reference counted generic data structures
written in C. Build system: plain Makefile (no configure script).
The upstream Makefile hardcodes CC=gcc and has no install target, so
this recipe drives make directly with the Conan toolchain compiler and
manually installs headers + static archive.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout

# 上游仅提供静态归档（Makefile 无 shared 目标），包按静态库建模，不声明 shared 选项
CFLAGS_BY_BUILD_TYPE = {
    "Release": "-O2",
    "Debug": "-O0 -g",
}


class OffbrandLibConan(ConanFile):
    name = "offbrand-lib"
    version = "1.0.0"
    description = "Reference counted generic data structures in C"
    license = "MIT"
    homepage = "https://github.com/theck01/offbrand_lib"
    url = "https://github.com/theck01/offbrand_lib"

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"offbrand-lib supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang")
        ar = comp.get("ar", "llvm-ar") if comp.get("ar") else "llvm-ar"

        src = self.source_folder
        # Upstream scripts/prepare (#!/bin/bash) is not portable (no /bin/bash on
        # the OHOS build host); create bin/ dirs directly and build only the
        # library archive target. -j1 avoids env jobserver mkfifo restrictions.
        for d in ("bin", "bin/objects", "bin/tests"):
            os.makedirs(os.path.join(src, d), exist_ok=True)
        opt = CFLAGS_BY_BUILD_TYPE.get(str(self.settings.build_type), "-O2")
        self.run(
            f"make -j1 CC='{cc}' AR='{ar}' CFLAGS='-Wall -Wextra {opt} -fPIC' "
            f"bin/offbrand.a",
            env="conanbuild",
            cwd=src,
        )

    def package(self):
        src = self.source_folder
        pkg_include = os.path.join(self.package_folder, "include")
        pkg_lib = os.path.join(self.package_folder, "lib")
        # No upstream install target: install headers + static archive manually.
        # keep_path=False flattens so files land directly in include/ and lib/.
        # 公共头与 private 头分别复制，避免 private 头在 include/ 根重复落盘。
        copy(self, "*.h", os.path.join(src, "include"), pkg_include,
             keep_path=False, excludes=["*_private.h"])
        copy(self, "*.h", os.path.join(src, "include", "private"),
             os.path.join(pkg_include, "private"), keep_path=False)
        copy(self, "offbrand.a", os.path.join(src, "bin"), pkg_lib, keep_path=False)
        # Rename to liboffbrand.a so CMakeDeps' lib<name>.a lookup succeeds
        os.rename(os.path.join(pkg_lib, "offbrand.a"), os.path.join(pkg_lib, "liboffbrand.a"))

    def package_info(self):
        self.cpp_info.libs = ["offbrand"]