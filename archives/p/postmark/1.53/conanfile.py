#!/usr/bin/env python3
"""Conan recipe for postmark 1.53 — NetApp PostMark file-system benchmark (single-file C, Makefile).

Build: make CC=clang -j1 postmark. Produces the `postmark` executable (CLI benchmark tool).
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PostmarkConan(ConanFile):
    name = "postmark"
    version = "1.53"
    description = "postmark — NetApp PostMark file-system benchmark (small-file I/O workload)"
    license = "Artistic-1.0"
    homepage = "https://packages.debian.org/source/sid/postmark"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # License 口径：以源码内含的 Artistic License 全文为准（NetApp 1997-2001）；
    # Debian 打包元数据另含 GPL-2+ 双许可说明，本配方采用 Artistic-1.0（源码自带许可）。

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compiler from Conan conf, never from bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # 单 C 源 Makefile，-j1 保证确定性构建
        self.run(f'make CC="{cc}" -j1 postmark', cwd=self.source_folder)

    def package(self):
        # Makefile install writes $(DESTDIR)/usr/bin; place binary at pkg/bin
        copy(self, "postmark", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
