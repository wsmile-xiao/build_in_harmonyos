#!/usr/bin/env python3
"""Conan recipe for net-tools 2.1 -- legacy Linux NET-3 network tools for HarmonyOS PC.

平台任务 contrib-5919 指定归档版本 2.1；上游版本序列为 1.60/2.0/2.10，
无独立 2.1 发布版，源码采用官方最新发布 net-tools-2.10.tar.xz（见 conandata.yml）。
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NetToolsConan(ConanFile):
    name = "net-tools"
    version = "2.1"
    description = "Legacy Linux NET-3 network tools (ifconfig/route/netstat/arp/hostname/...)"
    license = "GPL-2.0-or-later"
    homepage = "https://net-tools.sourceforge.net/"
    url = "https://downloads.sourceforge.net/project/net-tools/net-tools-2.10.tar.xz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _config_shell(self):
        return os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"

        config_shell = self._config_shell()
        self.run(f'yes "" | {config_shell} ./configure.sh config.in',
                 cwd=self.source_folder)

        extra = f"CC={cc} AR={ar} RANLIB={ranlib}"
        self.run(f"CPPFLAGS=-D__MUSL__ make {extra} -j1", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        bin_dir = os.path.join(self.package_folder, "bin")
        sbin_dir = os.path.join(self.package_folder, "sbin")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(sbin_dir, exist_ok=True)
        for b in ("ifconfig", "netstat", "route", "hostname"):
            copy(self, b, src, bin_dir)
        for b in ("nameif", "arp", "rarp", "iptunnel", "ipmaddr",
                  "mii-tool", "plipconfig", "slattach"):
            copy(self, b, src, sbin_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
