#!/usr/bin/env python3
"""Conan recipe — exiftags 1.01 (Makefile).

exiftags is a utility to parse and display Exif tags from JPEG files.
Build system: plain Makefile (no configure script).
Three executables are built: exiftags, exifcom, exiftime.
No external dependencies (only libc + libm).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ExiftagsConan(ConanFile):
    name = "exiftags"
    version = "1.01"
    description = "Utility to parse and display Exif tags in JPEG files"
    license = "BSD-4-Clause"
    homepage = "https://johnst.org/sw/exiftags/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use `in ("Linux", "OHOS")`, not == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"exiftags supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"

        src = self.source_folder
        # Plain Makefile build — no configure script.
        # R9: Always use -j1, never -j$(nproc)
        # E266 (revised): GNU ld 不注入 .codesign 段，OHOS 内核拒绝执行无签名 ELF；
        # 回到 clang 默认 lld 链接，lld 自动注入有效签名，二进制可直接执行。
        cflags = "-fPIC -O2"
        self.run(f"make CC='{cc}' CFLAGS='{cflags}' -j1", env="conanbuild", cwd=src)

    def package(self):
        # Copy the three executables and man pages into the package.
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "exiftags", self.source_folder, bindir)
        copy(self, "exifcom", self.source_folder, bindir)
        copy(self, "exiftime", self.source_folder, bindir)
        copy(self, "*.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        # lld 链接的二进制已带可执行位与 .codesign 段；chmod 仅作冗余保险。
        for name in ("exiftags", "exifcom", "exiftime"):
            os.chmod(os.path.join(bindir, name), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m"]
