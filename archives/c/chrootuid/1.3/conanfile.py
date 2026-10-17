#!/usr/bin/env python3
"""Conan recipe — chrootuid 1.3（Wietse Venema 的 chroot+setuid 执行器，单文件 C 工具）.

上游 ftp.porcupine.org 服务器不稳定（Windows/设备实测间歇 404/拒连），源码经
archive.ubuntu.com pristine orig.tar.gz 获取，Debian dsc 互证。raw Makefile：
注意 tarball 自带 1993 年的 i386 预编译 ELF `chrootuid`，必须先删除再 make，
否则目标新于源码导致静默跳过重编，打包出去的是 x86 旧产物。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ChrootuidConan(ConanFile):
    name = "chrootuid"
    version = "1.3"
    description = "chrootuid: run a command in a chroot sandbox as an unprivileged user"
    license = "Wietse-Venema-permissive"  # 见 chrootuid_license：保留版权声明即可自由使用与再分发（BSD 风格）
    homepage = "https://ftp.porcupine.org/pub/security/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # 单目录 raw Makefile，原地构建
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = os.path.join(".", "conan")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 关键：tarball 自带 i386 预编译 ELF `chrootuid`（1993 年），
        # 目标时间戳新于源码会让 make 静默跳过编译——先删除再构建
        prebuilt = os.path.join(self.source_folder, "chrootuid")
        if os.path.exists(prebuilt):
            os.remove(prebuilt)
        # CC 显式指定（make 默认 cc，设备 PATH 无 cc）；CFLAGS 保留上游 -O
        # 代码为 1993 年 K&R/C90 风格，现代 clang 需要 -Wno-deprecated 或默认告警即可
        self.run(
            "make CC=clang CFLAGS='-O' chrootuid",
            cwd=self.source_folder,
        )

    def package(self):
        # 上游 install 目标写死 /usr/local，不使用；手动按交付清单打包
        src = self.source_folder
        copy(self, "chrootuid", os.path.join(src), os.path.join(self.package_folder, "bin"))
        copy(self, "chrootuid.1", os.path.join(src), os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "README", os.path.join(src), os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "chrootuid_license", os.path.join(src), os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
