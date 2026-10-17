#!/usr/bin/env python3
"""Conan recipe for libdpkg-perl — dpkg 的 Perl 库（纯 Perl，无编译）。

libdpkg-perl 是 dpkg 源码树中 scripts/ 目录的 Perl 模块集（Dpkg.pm +
Dpkg/** 共 92 个 .pm），Debian 中单独打包（Architecture: all，纯 Perl）。
依赖：仅 dpkg + Perl 核心（libfile-fcntllock-perl 为 Recommends 非必需）。
package_type=application（本环境 python-require 型 conan create 静默
跳过构建——dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import download


class LibdpkgPerlConan(ConanFile):
    name = "libdpkg-perl"
    version = "1.23.7"
    package_type = "application"
    license = "GPL-2.0-or-later"
    homepage = "https://manpages.debian.org/libdpkg-perl"
    description = "libdpkg-perl — dpkg Perl modules (Dpkg::*, pure Perl, from dpkg source tree)"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        # dpkg 源码包含 tests/ 下的 FIFO 测试文件，OHOS 沙箱禁止创建 FIFO
        # （get() 解压报 Operation not permitted）——故只解压 scripts/
        # 子树（即 libdpkg-perl 内容，Dpkg.pm + Dpkg/**），绕开 FIFO。
        # 注：source() 阶段 self.build_folder 为 None，需用 self.source_folder。
        dl = os.path.join(self.source_folder, "dpkg_1.23.7.tar.xz")
        download(self, self.conan_data["sources"]["url"], dl,
                 retry=5, retry_wait=5)
        self.run(
            'tar -xJf "{}" -C "{}" --strip-components=1 "dpkg-1.23.7/scripts"'
            .format(dl, self.source_folder))
        os.remove(dl)

    def build(self):
        # 纯 Perl——无编译——安装 scripts/ 的 .pm 到 perl site-lib
        pass

    def package(self):
        scripts = os.path.join(self.source_folder, "scripts")
        dest = os.path.join(self.package_folder, "lib", "perl5")
        # 拷贝 Dpkg.pm + Dpkg/ 整树（92 个 .pm）
        shutil.copytree(scripts, dest, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(
                            "*.pl", "*.PL", "Makefile*", "*.in", "*.am",
                            "mk", "po", "completion", "dpkg-*",
                            "__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
