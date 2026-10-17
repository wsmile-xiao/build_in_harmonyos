#!/usr/bin/env python3
"""Conan recipe for disktype 9 — disk/image content format detection tool.

disktype is a pure Makefile project (no configure, no install target).
Build requires manual CPPFLAGS to enable Linux ioctl support on OHOS.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DisktypeConan(ConanFile):
    name = "disktype"
    version = "9.0"
    description = "Detect content format of a disk or disk image — 磁盘/磁盘镜像内容格式检测工具"
    license = "MIT"
    homepage = "https://disktype.sourceforge.net"
    url = "https://downloads.sourceforge.net/project/disktype/disktype/9/disktype-9.tar.gz"

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

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # disktype uses uname to detect platform; on OHOS, uname returns "HarmonyOS"
        # so USE_IOCTL_LINUX is not auto-enabled. We manually define it since
        # the OHOS kernel is Linux-based and ioctl works correctly.
        # Respect build_type setting instead of hardcoding optimization level
        if self.settings.build_type == "Debug":
            cflags = "-Wall -fPIC -g -O0"
        else:
            cflags = "-Wall -fPIC -O2"
        self.run(f'make CC={cc} CPPFLAGS="-D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 -DUSE_IOCTL_LINUX" CFLAGS="{cflags}" -j1',
                 cwd=self.source_folder)

    def package(self):
        # Copy the binary
        copy(self, "disktype", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Copy man page
        copy(self, "disktype.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        # Copy documentation
        for doc in ("README", "LICENSE", "HISTORY", "TODO"):
            copy(self, doc, self.source_folder, os.path.join(self.package_folder, "share", "doc", "disktype"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
