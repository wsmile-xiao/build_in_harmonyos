#!/usr/bin/env python3
"""Conan recipe for libcrc 2.0.

libcrc 上游只提供纯 GNU Makefile（无 configure 脚本，作者刻意不依赖
autoconf/automake），且上游明确只支持静态链接（Makefile 只生成 libcrc.a）。
因此本配方用 make 直接构建，不经过 AutotoolsToolchain。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibcrcConan(ConanFile):
    name = "libcrc"
    version = "2.0"
    description = "libcrc is a library to calculate various checksums of data. Includes CRC8, CRC16, CRC32, CRC-CCITT, CRC-DNP, CRC-Sick, CRC-Kermit, CRC-Xmodem, NMEA checksum."
    license = "MIT"
    homepage = "https://github.com/lammertb/libcrc"
    url = "https://github.com/lammertb/libcrc"

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
        # 纯 Makefile 构建；Makefile 默认 CC=cc，这里显式传入 Conan 工具链编译器。
        # 平台编译器从 settings 推导（clang 用于 OHOS/Linux）。
        cc = "clang"
        self.run(f"make CC={cc} LINK={cc} all", cwd=self.source_folder)

    def package(self):
        # conan copy() 会把 pattern 的相对路径拼接到 dst 之后，因此 dst 必须
        # 是 package_folder 本身，才能得到 package/lib/libcrc.a 与
        # package/include/checksum.h 的正确布局。
        copy(self, "lib/libcrc.a", src=self.source_folder, dst=self.package_folder)
        copy(self, "include/checksum.h", src=self.source_folder, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["crc"]
