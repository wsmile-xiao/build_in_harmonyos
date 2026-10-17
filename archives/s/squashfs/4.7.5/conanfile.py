#!/usr/bin/env python3
"""Conan recipe for squashfs-tools (mksquashfs/unsquashfs).

Command-line tools for creating and extracting squashfs filesystems.
Built with gzip-only compression support (other compressors need dev packages
not available on OHOS).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SquashfsConan(ConanFile):
    name = "squashfs"
    version = "4.7.5"
    description = "Compressed read-only file system for Linux"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/plougher/squashfs-tools"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # Uses system zlib (-lz)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The tarball has squashfs-tools/ subdirectory — flatten it to root
        import shutil
        sub = os.path.join(self.source_folder, "squashfs-tools")
        if os.path.isdir(sub):
            for item in os.listdir(sub):
                src = os.path.join(sub, item)
                dst = os.path.join(self.source_folder, item)
                shutil.move(src, dst)
            os.rmdir(sub)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # Build with gzip-only support (XZ/LZO/LZ4/ZSTD need dev packages not available on OHOS)
        # Use -C to run make in the source folder (Makefile is there, not in build folder)
        self.run(f"make -C {self.source_folder} CC={cc} XZ_SUPPORT=0 LZO_SUPPORT=0 LZ4_SUPPORT=0 ZSTD_SUPPORT=0 -j1")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "mksquashfs", self.source_folder, bindir)
        copy(self, "unsquashfs", self.source_folder, bindir)
        copy(self, "sqfstar", self.source_folder, bindir)
        copy(self, "sqfscat", self.source_folder, bindir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["z", "pthread", "m"]
