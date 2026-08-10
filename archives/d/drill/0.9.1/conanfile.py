#!/usr/bin/env python3
"""Conan recipe — drill 0.9.1（DNS 查询工具）.

drill 是 NLnet Labs 的 DNS 查询工具（类似 dig）。drill 0.9.1 独立源码
已下线（官方自 ldns 1.0.0 起并入 ldns），本配方基于 ldns 源码
（ldns-1.9.1.tar.gz）构建 drill 组件。
构建系统：GNU Autotools（configure --with-drill）
平台：OHOS aarch64 / Linux / macOS
依赖：openssl（DNSSEC）
"""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, Autotools, PkgConfigDeps


class DrillConan(ConanFile):
    name = "drill"
    version = "0.9.1"
    description = "drill — DNS query tool (NLnet Labs, built from ldns source)"
    license = "BSD-3-Clause"
    homepage = "https://www.nlnetlabs.nl/projects/ldns/"
    url = "https://github.com/NLnetLabs/ldns"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _machine(self, arch):
        # 从 arch setting 推导 GNU 三元组 machine 部分
        return {
            "armv8": "aarch64",
            "armv7": "arm",
            "x86_64": "x86_64",
            "x86": "i686",
        }.get(str(arch), str(arch))

    def generate(self):
        # 生成 openssl 依赖的 .pc 文件（ldns configure 用 pkg-config 查找）
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # 启用 drill 组件构建
        tc.configure_args.append("--with-drill")
        # 静态链接：ldns 默认构建共享库（libldns.so），package 仅打包 drill
        # 二进制会导致运行时找不到 libldns.so（--help 输出动态库错误而非
        # usage）；--disable-shared 产出静态 libldns.a，drill 单二进制可运行
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        # ldns 的 acx_openssl.m4 在硬编码路径（/usr/local/ssl 等）查找 openssl，
        # openssl 是 conan 依赖包不在这些路径；用 --with-ssl 指向 conan openssl
        # 安装前缀（含 include/openssl/ssl.h + lib/），并注入 CPPFLAGS/LDFLAGS
        openssl_pkg = self.dependencies["openssl"].package_folder
        tc.configure_args.append(f"--with-ssl={openssl_pkg}")
        ssl_inc = os.path.join(openssl_pkg, "include")
        ssl_lib = os.path.join(openssl_pkg, "lib")
        tc.configure_args.extend([
            f"CPPFLAGS=-I{ssl_inc}",
            f"LDFLAGS=-L{ssl_lib}",
        ])
        # ldns 的 config.guess 可能无法识别 HarmonyOS，指定 --build/--host 三元组
        machine = self._machine(self.settings.arch)
        triplet = f"{machine}-unknown-linux-gnu"
        tc.configure_args.extend([f"--build={triplet}", f"--host={triplet}"])
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        # OHOS 沙箱 umask 077 导致 config.status 临时目录不可写，临时改 022
        old_umask = os.umask(0o022)
        try:
            autotools.configure()
            # 只构建 drill 组件（-j1 避免 mkfifo 沙箱限制）
            autotools.make(args=["-j1"])
        finally:
            os.umask(old_umask)

    def package(self):
        # drill 二进制在 ldns 源码的 drill/ 目录，手动复制到 bin/
        from conan.tools.files import copy
        copy(self, "drill", os.path.join(self.build_folder, "drill"),
             os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []