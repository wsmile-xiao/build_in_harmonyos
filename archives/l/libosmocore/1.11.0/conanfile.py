#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
libosmocore/1.11.0 — Osmocom 基础库集（OpenHarmony PC / aarch64 适配配方）

上游:    https://osmocom.org/projects/libosmocore
发布包:  https://downloads.osmocom.org/releases/libosmocore/libosmocore-1.11.0.tar.bz2

包内容（10 个库）:
  libosmocore  libosmocodec  libosmocoding  libosmoctrl  libosmogb
  libosmogsm   libosmoisdn   libosmosim     libosmousb   libosmovty

适配要点（完整说明见 notes.md 与 reports/test-report.md）:
  1. 原生 TLS（关键项）: OHOS clang 默认使用模拟 TLS（emutls）。libosmocore 在公共头文件中以
     `extern __thread` 暴露线程局部变量（osmocom/core/talloc.h 的 osmo_ctx、
     osmocom/gsm/cbsp.h 的 osmo_cbsp_errstr）。libtool 的 -export-dynamic 会把头文件里的
     `extern __thread` *声明* 也导出为 emutls 引用，使库自身带上 `__emutls_v.<符号>` 未定义
     引用；实测「库 emutls + 调用方原生 TLS」组合在运行时段错误（对照实验见 notes.md）。
     因此统一按原生 TLS 构建：构建期注入 -fno-emulated-tls，并通过 cpp_info 传播给消费者，
     避免跨 DSO 的 TLS 模型不一致。
  2. 上游测试: build() 内执行上游完整测试套件 `make check`（88 passed / 2 skipped）。
  3. SCTP:     平台 sysroot 无 libsctp，内核亦不支持 SCTP
     （socket(AF_INET, SOCK_STREAM, IPPROTO_SCTP) → errno 93 EPROTONOSUPPORT）；configure 的
     PKG_CHECK_MODULES 探测失败后走 AC_SEARCH_LIBS 兜底并以 AC_MSG_ERROR 失败 →
     显式 --disable-libsctp（socket_sctp 测试随上游条件自然跳过）。
  4. io_uring: 平台 seccomp 阻断 io_uring 系统调用（io_uring_queue_init() 返回 0 后进程即
     SIGSYS 核心转储，实测见 notes.md）→ 显式 --disable-uring。
  5. gnutls:   可选 crypto 后端，制品仓无该依赖 → 显式 --disable-gnutls。
  6. 发布包缺 src/gsm/kdf/crypto.h（上游打包遗漏，kdf/sha1.c、kdf/sha256.c 直接 #include），
     由 patches/0012-src-gsm-kdf-crypto.h.patch 以 1.11.0 tag 原文补齐。
"""

import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, rm, rmdir)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualRunEnv

required_conan_version = ">=2.0"


class LibosmocoreConan(ConanFile):
    name = "libosmocore"
    version = "1.11.0"
    description = ("Osmocom core libraries: utility, logging, vty, select loop, message buffers, "
                   "GSM/GPRS protocols, codecs, SIM/PCSC, USB and control interface")
    license = "GPL-2.0-or-later"
    url = "https://osmocom.org/projects/libosmocore"
    homepage = "https://osmocom.org/projects/libosmocore"
    topics = ("osmocom", "gsm", "telephony", "talloc", "logging", "vty")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libmnl": [True, False],
        "with_libusb": [True, False],
        "with_pcsc": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_libmnl": True,
        "with_libusb": True,
        "with_pcsc": True,
    }

    exports_sources = "patches/**"

    # libosmocore 通过公共头文件导出线程局部变量（osmo_ctx / osmo_cbsp_errstr）。
    # OHOS clang 默认 -femulated-tls，跨 DSO 使用模拟 TLS 的变量在运行时段错误；
    # 库与消费者必须使用同一 TLS 模型，故统一使用原生 TLS（详见 notes.md 的对照实验）。
    NATIVE_TLS_FLAG = "-fno-emulated-tls"

    # 组件与依赖关系取自上游 libosmo*.pc 的 Requires 字段（各库之间的真实依赖）
    LIB_COMPONENTS = {
        "osmocodec": ["osmocore"],
        "osmocoding": ["osmocore", "osmogsm", "osmocodec"],
        "osmocore": [],
        "osmoctrl": ["osmocore", "osmogsm"],
        "osmogb": ["osmocore", "osmovty", "osmogsm"],
        "osmogsm": ["osmocore", "osmoisdn"],
        "osmoisdn": ["osmocore"],
        "osmosim": ["osmocore"],
        "osmousb": ["osmocore"],
        "osmovty": ["osmocore"],
    }

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
        # 公共头文件直接暴露依赖头文件（talloc.h / libusb.h / libmnl/libmnl.h），
        # 且 talloc 为 static-library 类型：Conan 对 static-library 依赖默认不传递
        # headers/libs，CMakeDeps 会静默丢掉组件里的 talloc::talloc 引用，
        # 导致下游（含 CI test_package）编译时报 'talloc.h' file not found。
        # 显式声明传递性，保证下游能解析全部依赖头文件与链接项。
        self.requires("talloc/2.4.4", transitive_headers=True, transitive_libs=True)
        if self.options.with_libmnl:
            self.requires("libmnl/1.0.5", transitive_headers=True, transitive_libs=True)
        if self.options.with_libusb:
            self.requires("libusb/1.0.27", transitive_headers=True, transitive_libs=True)
        if self.options.with_pcsc:
            self.requires("pcsc-lite/2.4.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 1) 原生 TLS（见类注释第 1 条与 NATIVE_TLS_FLAG）
        tc.extra_cflags.append(self.NATIVE_TLS_FLAG)
        tc.extra_cxxflags.append(self.NATIVE_TLS_FLAG)
        # 2) 平台能力开关：SCTP / io_uring / gnutls 在本平台不可用（见类注释第 3~5 条）
        tc.configure_args.append("--disable-gnutls")
        tc.configure_args.append("--disable-libsctp")
        tc.configure_args.append("--disable-uring")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        if not self.options.with_libmnl:
            tc.configure_args.append("--disable-libmnl")
        if not self.options.with_libusb:
            tc.configure_args.append("--disable-libusb")
        if not self.options.with_pcsc:
            tc.configure_args.append("--disable-pcsc")
        tc.generate()
        # 依赖的 pkg-config 元数据（talloc / libmnl / libusb-1.0 / libpcsclite）
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # Expose the runtime library paths of the host dependencies to the in-tree
        # programs: the sim test loads libpcsclite.so.1 at runtime, which is not on
        # any global library search path in the build container.
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
        # 上游只提供 pkg-config 元数据（无 CMake 配置文件），这里按库拆分组件，
        # 消费者可用 CMake 目标 libosmocore::<库名> 或 pkg-config 名 libosmo<库名>
        for name, requires in self.LIB_COMPONENTS.items():
            cpp = self.cpp_info.components[name]
            cpp.libs = [name]
            cpp.set_property("pkg_config_name", "lib" + name)
            cpp.requires = ["talloc::talloc"] + list(requires)  # 组件间依赖直接写组件名
            # 跨 DSO 的原生 TLS：消费者必须与库使用同一 TLS 模型
            cpp.cflags = [self.NATIVE_TLS_FLAG]
            cpp.cxxflags = [self.NATIVE_TLS_FLAG]
        if self.options.with_libmnl:
            self.cpp_info.components["osmocore"].requires.append("libmnl::libmnl")
        if self.options.with_libusb:
            self.cpp_info.components["osmousb"].requires.append("libusb::libusb")
        if self.options.with_pcsc:
            self.cpp_info.components["osmosim"].requires.append("pcsc-lite::pcsc-lite")
