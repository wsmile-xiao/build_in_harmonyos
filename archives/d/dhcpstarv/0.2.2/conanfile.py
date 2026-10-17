#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Dhcpstarv, dhcpstarv, 0.2.2, dhcpstarv 0.2.2, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DhcpstarvConan(ConanFile):
    name = "dhcpstarv"
    version = "0.2.2"
    description = "dhcpstarv 0.2.2"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.configure_args.append("--prefix=/storage/Users/currentUser/usr/local")
        tc.configure_args.append("--disable-silent-rules")
        tc.configure_args.append("--disable-silent-rules")
        tc.configure_args.append("--disable-silent-rules")
        tc.configure_args.append("--disable-silent-rules")
        tc.configure_args.append("--disable-silent-rules")
        tc.configure_args.append("--disable-silent-rules")
        tc.configure_args.append("--disable-silent-rules")
        tc.configure_args.append("--disable-silent-rules")
        tc.configure_args.append("--disable-silent-rules")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # r44: 0000 预生成文件经 patch 逐文件写盘后，Makefile.in 的 mtime 可能早于其规则
        # 依赖 aclocal.m4，使 VPATH Makefile 维护规则判定 Makefile.in 过期并调用缺失的
        # automake-1.16。此处按 st_mtime_ns 精确归一化：仅当 source_folder 内 Makefile.in
        # 与 aclocal.m4 同时存在时，令 Makefile.in 的 mtime 不早于 aclocal.m4；任一缺失则
        # 安全跳过，不创建文件、不改内容、不写死时间值。
        mk_in = os.path.join(self.source_folder, "Makefile.in")
        ac_m4 = os.path.join(self.source_folder, "aclocal.m4")
        if os.path.exists(mk_in) and os.path.exists(ac_m4):
            dep_mtime_ns = os.stat(ac_m4).st_mtime_ns
            if os.stat(mk_in).st_mtime_ns < dep_mtime_ns:
                os.utime(mk_in, ns=(dep_mtime_ns, dep_mtime_ns))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # application/CLI: 包内无库产物，不声明 cpp_info.libs（r44）
        pass
