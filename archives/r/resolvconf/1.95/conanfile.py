#!/usr/bin/env python3
"""Conan recipe — resolvconf 1.95 (Debian name server information handler).

Pure shell-script network configuration tool that manages /etc/resolv.conf.
No compilation; build system is Debian debhelper (copy-only in Conan context).
License: GPL-2+

R40 适配完整性: 基础适配（路径 A）。resolvconf 主脚本硬编码 /usr/lib/resolvconf/
等系统路径，不读取 RESOLVCONF_LIB 环境变量，故 -a/-d/-u 等核心操作在 Conan 包
环境中不可用，仅 --help/--version 和直接调用 normalize-resolvconf 可用。
Conan 包作为分发载体，部署到系统标准路径后全部功能正常。详见 notes.md。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class ResolvconfConan(ConanFile):
    name = "resolvconf"
    version = "1.95"
    description = "name server information handler — framework for keeping up to date the system's information about name servers"
    license = "GPL-2+"
    homepage = "https://salsa.debian.org/debian/resolvconf"
    url = "https://salsa.debian.org/debian/resolvconf"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def build(self):
        pass

    def package(self):
        source_dir = self.source_folder
        bin_src = os.path.join(source_dir, "bin")
        # Main executable
        copy(self, "resolvconf", src=bin_src,
             dst=os.path.join(self.package_folder, "bin"))
        # Helper scripts referenced by resolvconf (upstream: /usr/lib/resolvconf/)
        copy(self, "list-records", src=bin_src,
             dst=os.path.join(self.package_folder, "lib", "resolvconf"))
        copy(self, "normalize-resolvconf", src=bin_src,
             dst=os.path.join(self.package_folder, "lib", "resolvconf"))
        copy(self, "dump-debug-info", src=bin_src,
             dst=os.path.join(self.package_folder, "share", "resolvconf"))
        # Configuration files
        copy(self, "*", src=os.path.join(source_dir, "etc"),
             dst=os.path.join(self.package_folder, "share", "resolvconf", "etc"))
        # Manpages
        copy(self, "*.8", src=os.path.join(source_dir, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "*.5", src=os.path.join(source_dir, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man5"))
        # License and docs
        copy(self, "COPYING", src=source_dir,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README", src=source_dir,
             dst=os.path.join(self.package_folder, "share", "doc", "resolvconf"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.define_path(
            "RESOLVCONF_BIN",
            os.path.join(self.package_folder, "bin", "resolvconf"))
        self.runenv_info.define_path(
            "RESOLVCONF_LIB",
            os.path.join(self.package_folder, "lib", "resolvconf"))
