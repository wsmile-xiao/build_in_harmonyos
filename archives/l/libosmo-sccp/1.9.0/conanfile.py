#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
libosmo-sccp/1.9.0 — Osmocom SCCP / SIGTRAN 协议栈（OpenHarmony PC / aarch64 适配配方）

上游:    https://osmocom.org/projects/libosmo-sccp
发布包:  https://downloads.osmocom.org/releases/libosmo-sccp/libosmo-sccp-1.9.0.tar.bz2

包内容:
  libosmo-sigtran.so*   （主库: M3UA/SUA/SCCP/xUA/IPA，soname libosmo-sigtran.so.10）
  libsccp.a / libmtp.a  （legacy 静态库）
  libxua.a              （legacy 静态库）
  bin/osmo-stp          （信号转接点可执行）
  include/osmocom/{sccp,sigtran,mtp}/ 公共头

适配要点（完整说明见 notes.md 与 reports/test-report.md）:
  1. SCTP: 平台无 libsctp 且内核不支持 SCTP（EPROTONOSUPPORT，与 libosmocore/
     libosmo-netif 同源结论）→ configure --disable-libsctp（上游 configure.ac 无此
     开关，补丁 0004 新增，并把硬 AC_MSG_ERROR 降级为警告）。HAVE_LIBSCTP 未定义后，
     上游"总是有 SCTP"假设的代码路径需守卫（补丁 0005~0009）：
       - netinet/sctp.h / osmocom/netif/sctp.h include 守卫（4 文件）；
       - osmo_ss7_asp.c 的 SCTP 通知处理/log_sctp_notification/
         peer|primary 主地址 setsockopt 簇函数与调用点守卫；
       - osmo_ss7_vty.c 的 SCTP 主地址应用调用点守卫。
  2. multiaddr: libosmocore(--disable-libsctp) 不导出 osmo_sock_multiaddr_* 系列，
     本包在 src/osmo_ss7.c 尾部按 !HAVE_LIBSCTP 提供单地址回退实现
     （osmo_sock_get_ip_and_port 回退 + 纯格式化；SCTP-only 多宿主 add/del 视为
     成功 no-op——单宿主 socket 的绑定地址集在 bind/connect 时已固定）。
  3. struct tcp_info: OHOS netinet/tcp.h 在 _GNU_SOURCE 下才定义 struct tcp_info
     → osmo_ss7_vty.c 顶部 define _GNU_SOURCE。
  4. 原生 TLS: 与 libosmocore/libosmo-netif 一致 -fno-emulated-tls，跨 DSO TLS
     模型统一（libosmocore 公共头暴露 extern __thread 变量）。
  5. 上游测试: build() 内执行 `make check`（5 用例全部通过：m2ua/mtp/sccp/xua/ss7）。
"""

import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, rm, rmdir)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualRunEnv

required_conan_version = ">=2.0"


class LibosmoSccpConan(ConanFile):
    name = "libosmo-sccp"
    version = "1.9.0"
    description = ("Osmocom SCCP/SIGTRAN stack: SCCP, M3UA, SUA, xUA, IPA and "
                   "the osmo-stp signal transfer point")
    license = "GPL-2.0-or-later"
    url = "https://osmocom.org/projects/libosmo-sccp"
    homepage = "https://osmocom.org/projects/libosmo-sccp"
    topics = ("osmocom", "sccp", "sigtran", "m3ua", "sua", "ss7", "stp")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    exports_sources = "patches/**"

    # 与 libosmocore 一致：原生 TLS（-fno-emulated-tls），跨 DSO TLS 模型统一
    NATIVE_TLS_FLAG = "-fno-emulated-tls"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def requirements(self):
        # 上游 configure.ac: libosmocore/libosmovty/libosmogsm >= 1.10.0
        # + libosmo-netif >= 1.5.0。libosmocore/1.11.0 与 libosmo-netif/1.6.0
        # 均已发布（W0 conan download EXIT=0），传递 talloc/libmnl 等依赖。
        self.requires("libosmocore/1.11.0",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libosmo-netif/1.6.0",
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 1) 原生 TLS（与 libosmocore 一致）
        tc.extra_cflags.append(self.NATIVE_TLS_FLAG)
        tc.extra_cxxflags.append(self.NATIVE_TLS_FLAG)
        # 2) 平台能力开关
        tc.configure_args.append("--disable-libsctp")   # 平台无 libsctp/SCTP
        tc.configure_args.append("--disable-doxygen")
        # 注意：AutotoolsToolchain 对 library+shared 会自动附加
        # `--enable-shared --disable-static`。但上游测试 Makefile 用
        # `-static -no-install` 链接 libosmo-sigtran（需要含全部符号的 .a，而
        # .so 仅导出 osmo_* 符号），因此必须同时构建 .so 与 .a：
        # 显式追加 `--enable-static`（autoconf 对 repeated enable/disable
        # 选项 last-wins，会同时产出两种库）；多余产物在 package() 中清理。
        tc.configure_args.append("--enable-static")
        tc.generate()
        # 依赖 pkg-config 元数据（libosmocore 家族）
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # 补丁 0004 修改 configure.ac 使其 mtime 新于 aclocal.m4/Makefile.in，
        # make 会尝试用 automake-1.16 重建（本机/CI 无该版本）。touch 全部生成文件，
        # 使其不旧于 configure.ac，避免无谓的 automake 重建（内容无需重新生成）。
        for _root, _dirs, files in os.walk(self.source_folder):
            for _f in files:
                if _f == "Makefile.in" or _f in ("aclocal.m4", "configure",
                                                 "config.h.in"):
                    os.utime(os.path.join(_root, _f), None)
        env = VirtualRunEnv(self).environment().vars(self, scope="run")
        with env.apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            # 上游测试套件（make check，5 用例全通过：m2ua/mtp/sccp/xua/ss7）
            autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            # 主库静态副本仅 shared 模式移除；legacy 静态库（libsccp/libmtp/
            # libxua）上游只以静态形式提供，始终保留。
            rm(self, "libosmo-sigtran.a", os.path.join(self.package_folder, "lib"))
        else:
            # 纯静态模式：移除主库的共享对象
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "etc"))

    def package_info(self):
        # 主库 libosmo-sigtran（含 M3UA/SUA/SCCP/xUA/IPA 全部实现）
        self.cpp_info.set_property("cmake_file_name", "libosmo-sigtran")
        self.cpp_info.set_property("cmake_target_name", "libosmo-sigtran::libosmo-sigtran")
        self.cpp_info.set_property("pkg_config_name", "libosmo-sigtran")
        self.cpp_info.libs = ["osmo-sigtran"]
        self.cpp_info.requires = ["libosmocore::osmocore",
                                  "libosmocore::osmovty",
                                  "libosmocore::osmogsm",
                                  "libosmo-netif::libosmo-netif"]
        # 跨 DSO 的原生 TLS：消费者必须与库使用同一 TLS 模型
        self.cpp_info.cflags = [self.NATIVE_TLS_FLAG]
        self.cpp_info.cxxflags = [self.NATIVE_TLS_FLAG]

        # legacy 静态库（对应上游 libosmo-sccp.pc / libosmo-mtp.pc / libosmo-xua.pc）
        self.cpp_info.components["sccp"].set_property("pkg_config_name", "libosmo-sccp")
        self.cpp_info.components["sccp"].libs = ["sccp"]
        self.cpp_info.components["sccp"].requires = ["libosmocore::osmocore"]
        self.cpp_info.components["mtp"].set_property("pkg_config_name", "libosmo-mtp")
        self.cpp_info.components["mtp"].libs = ["mtp"]
        self.cpp_info.components["mtp"].requires = ["libosmocore::osmocore"]
        self.cpp_info.components["xua"].set_property("pkg_config_name", "libosmo-xua")
        self.cpp_info.components["xua"].libs = ["xua"]
        self.cpp_info.components["xua"].requires = ["libosmocore::osmocore"]

        # osmo-stp 可执行（R38：软件级 commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
