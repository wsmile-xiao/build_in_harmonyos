#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
libosmo-abis/2.0.0 — Osmocom A-bis interface library（OpenHarmony PC / aarch64 适配配方）

上游:    https://osmocom.org/projects/libosmo-abis
发布包:  https://downloads.osmocom.org/releases/libosmo-abis/libosmo-abis-2.0.0.tar.bz2

包内容（2 个库）:
  libosmoabis   A-bis 接口抽象层（E1/T1 与 IP 承载，LAPD/IAPA 驱动，子通道复用/解复用）
  libosmotrau   TRAU 帧处理（加密模式算法 + RTP 帧转换）

适配要点（完整说明见 notes.md）:
  1. 原生 TLS: 与 libosmocore/1.11.0、libosmo-netif/1.6.0 一致（-fno-emulated-tls），
     跨 DSO 统一 TLS 模型。
  2. ortp:     上游默认启用（--enable-ortp），OHOS 适配惯例 --disable-ortp
     （libosmotrau 的 osmo_ortp.c 不编译，rtp_test 随 AT_SKIP_IF 自然跳过）。
  3. dahdi:    上游默认启用并 AC_CHECK_HEADERS(dahdi/user.h) 找不到即 AC_MSG_ERROR 硬失败；
     本平台无 DAHDI → 显式 --disable-dahdi（e1_input.c 中调用点已有 HAVE_DAHDI_USER_H 守卫）。
  4. e1d:      上游默认关闭（--enable-e1d 才启用），不引入。
  5. mISDN:    src/input/misdn.c 无条件 #include <mISDNif.h>。上游 tarball 自带
     include/mISDNif.h（-I$(top_srcdir)/include 命中），其 `#ifdef linux` 分支引入内核
     uapi <linux/socket.h>；OHOS sysroot 的 linux/socket.h 重定义 struct sockaddr_storage，
     与 <sys/socket.h> 冲突（libosmocore 0007 系同类问题）。补丁 0004 改为无条件使用
     libc sys 头（sa_family_t/AF_* 均由其提供）。
  6. ipa_recv 测试: musl strerror(EIO) 文案为 "I/O error"（glibc 为 "Input/output
     error"），.ok 期望文件按 glibc 文案 → 补丁 0005 对齐 libc 文案（libosmocore
     0023/0025 同类）。
  7. 上游测试: build() 内执行 make check（11 用例：10 PASS + 1 SKIP——rtp_test 因
     --disable-ortp 按上游 AT_SKIP_IF 跳过）。
"""

import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, rm, rmdir)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualRunEnv

required_conan_version = ">=2.0"


class LibosmoAbisConan(ConanFile):
    name = "libosmo-abis"
    version = "2.0.0"
    description = ("Osmocom A-bis interface libraries: E1/T1 and IP-based ETSI/3GPP "
                   "A-bis abstraction (LAPD/IPA drivers, subchannel mux/demux) and "
                   "TRAU frame handling with RTP conversion")
    license = "AGPL-3.0-or-later"
    url = "https://osmocom.org/projects/libosmo-abis"
    homepage = "https://osmocom.org/projects/libosmo-abis"
    topics = ("osmocom", "abis", "gsm", "trau", "lapd", "ipa")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    exports_sources = "patches/**"

    # 与 libosmocore 一致：公共头经 libosmocore 导出线程局部变量（osmo_ctx），
    # 库与消费者必须使用同一 TLS 模型（详见 libosmocore 1.11.0 notes.md）。
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
        # 上游 configure.ac（真实依赖声明）:
        #   PKG_CHECK_MODULES(LIBOSMOCORE,  libosmocore >= 1.11.0)
        #   PKG_CHECK_MODULES(LIBOSMOVTY,   libosmovty  >= 1.11.0)
        #   PKG_CHECK_MODULES(LIBOSMOGSM,   libosmogsm  >= 1.11.0)
        #   PKG_CHECK_MODULES(LIBOSMOCODEC, libosmocodec >= 1.11.0)
        #   PKG_CHECK_MODULES(LIBOSMONETIF, libosmo-netif >= 1.6.0)
        # osmovty/osmogsm/osmocodec 由 libosmocore 同一 conan 包提供（其
        # LIB_COMPONENTS），故仅需 requires libosmocore + libosmo-netif。
        # 公共头（e1_input.h 等）直接暴露 osmocom/core 与 osmocom/netif 头文件，
        # 显式声明传递性保证下游可解析。
        self.requires("libosmocore/1.11.0", transitive_headers=True, transitive_libs=True)
        self.requires("libosmo-netif/1.6.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 1) 原生 TLS（见类注释第 1 条）
        tc.extra_cflags.append(self.NATIVE_TLS_FLAG)
        tc.extra_cxxflags.append(self.NATIVE_TLS_FLAG)
        # 2) 平台能力开关（见类注释第 2~4 条）:
        #    ortp 默认启用但本平台不引入（glib/gstreamer 重链）；
        #    dahdi 默认启用且探测失败硬失败，本平台无 DAHDI；
        #    e1d 上游默认关闭，无需显式参数。
        tc.configure_args.append("--disable-ortp")
        tc.configure_args.append("--disable-dahdi")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()
        # 依赖的 pkg-config 元数据（libosmocore 家族 + libosmo-netif）
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # 在树内测试程序（tests/ 的 check_PROGRAMS）链接 libosmo* 共享库，
        # 运行期需 host 依赖库路径可见。
        env = VirtualRunEnv(self).environment().vars(self, scope="run")
        with env.apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()
            # 上游完整测试套件（CI L1.1 上游测试执行验证依赖此步骤）
            autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        # 上游仅 pkg-config 元数据（libosmoabis.pc: Requires libosmocore,
        # Requires.private libosmo-netif；libosmotrau.pc: Requires libosmocore）。
        # 两个库拆成组件，消费者可用 pkg-config 名 libosmoabis / libosmotrau。
        for comp, pkg_name in (("osmoabis", "libosmoabis"),
                               ("osmotrau", "libosmotrau")):
            cpp = self.cpp_info.components[comp]
            cpp.libs = [comp]
            cpp.set_property("pkg_config_name", pkg_name)
            cpp.requires = ["libosmocore::osmocore",
                            "libosmocore::osmogsm",
                            "libosmocore::osmovty"]
            # 跨 DSO 的原生 TLS：消费者必须与库使用同一 TLS 模型
            cpp.cflags = [self.NATIVE_TLS_FLAG]
            cpp.cxxflags = [self.NATIVE_TLS_FLAG]
        self.cpp_info.components["osmoabis"].requires.append("libosmo-netif::libosmo-netif")
        # libosmotrau 的 LIBADD 含 libosmocodec（raa_prime 编解码）
        self.cpp_info.components["osmotrau"].requires.append("libosmocore::osmocodec")
