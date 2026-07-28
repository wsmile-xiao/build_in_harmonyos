#!/usr/bin/env python3
"""Conan recipe — iproute2 6.11.0 (Makefile + hand-written configure).

iproute2 is a set of command-line tools (ip/tc/bridge/ss/...), NOT a library.
It ships its own ./configure (feature probing → config.mk) and a recursive
GNU Makefile driven by the SUBDIRS variable.

OHOS adaptation (see notes.md / knowledge E215, E216):
  - R26: terminal tools statically linked (LDFLAGS=-static). getpass is not
         exported by OHOS libc.so but the static libc.a provides a real
         implementation, so a declaration + -static resolves it (E215).
  - E216: kernel UAPI headers redefine in6_addr/sockaddr_in6/ipv6_mreq vs musl
         <netinet/in.h>. Force musl to define them first (compat header) and
         silence the kernel UAPI copies with -D__UAPI_DEF_*=0.
  - Only the core tools are built: SUBDIRS="lib ip tc bridge misc genl".
    * netem is dropped: it contains HOST tools (maketable/normal) that must be
      built with the host gcc, not the target flags.
    * tipc/devlink/rdma/dcb are dropped: they require libmnl, which is not yet
      in the OHOS sysroot (dependency-chain boundary, not a blocker here).

R32: settings.os is handled for both "Linux" and "OHOS".
R33: the compiler is taken from Conan conf, never from ${CC}/${CFLAGS} env.
R9:  make -j1.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Iproute2Conan(ConanFile):
    name = "iproute2"
    version = "6.11.0"
    description = "Linux 网络配置工具集（ip/tc/bridge/ss 等）"
    license = "GPL-2.0-or-later"
    homepage = "https://wiki.linuxfoundation.org/networking/iproute2"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Core tools only. netem (host-only helpers) and the libmnl-dependent
    # tipc/devlink/rdma/dcb are intentionally excluded (see notes.md).
    _subdirs = "lib ip tc bridge misc genl"

    # UAPI guards that let musl <netinet/in.h> win over the kernel UAPI copies
    # (E216). Kept as a class attribute so build() and package() stay in sync.
    _uapi_guards = " ".join([
        "-D__UAPI_DEF_IN6_ADDR=0",
        "-D__UAPI_DEF_SOCKADDR_IN6=0",
        "-D__UAPI_DEF_IPV6_MREQ=0",
        "-D__UAPI_DEF_IN6_PKTINFO=0",
        "-D__UAPI_DEF_IP6_MTUINFO=0",
        "-D__UAPI_DEF_IPV6_OPTIONS=0",
        "-D__UAPI_DEF_IN6_ADDR_ALT=0",
    ])

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── helpers ──────────────────────────────────────────────────────────
    def _cc(self):
        # R33: compiler from Conan conf, not from shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("c", "clang")

    def _config_shell(self):
        # R5/R32: OHOS has no /bin/sh. Prefer the CONFIG_SHELL injected by the
        # profile [buildenv] (conanbuild env is applied to self.run); fall back
        # to an OS-appropriate default so the recipe also works on plain Linux.
        fallback = "/data/service/hnp/bin/bash" if self.settings.os == "OHOS" else "/bin/sh"
        return "${CONFIG_SHELL:-%s}" % fallback

    def _ccopts(self):
        # -include uses an ABSOLUTE path: subdir compiles run from ip/, tc/, ...
        # so a relative path would not resolve (matches the verified local build).
        compat = os.path.join(self.source_folder, "include", "ohos_compat.h")
        return (
            f"-O2 -pipe -include {compat} "
            "-Wno-implicit-function-declaration -Wno-int-conversion "
            f"{self._uapi_guards}"
        )

    def _make_vars(self):
        return (
            f'SUBDIRS="{self._subdirs}" '
            f'CC="{self._cc()}" '
            f'CCOPTS="{self._ccopts()}" '
            'LDFLAGS="-static"'
        )

    # ── build ────────────────────────────────────────────────────────────
    def build(self):
        # Creates include/ohos_compat.h (getpass decl + musl-first net headers).
        apply_conandata_patches(self)

        # iproute2's configure probes kernel/libc features and writes config.mk.
        # Run it with the target CC so detection matches OHOS.
        self.run(
            f'CC="{self._cc()}" {self._config_shell()} configure',
            cwd=self.source_folder,
        )

        # R9: -j1. Core tools only (SUBDIRS override).
        self.run(
            f"make {self._make_vars()} -j1",
            cwd=self.source_folder,
        )

    # ── package ──────────────────────────────────────────────────────────
    def package(self):
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # `install` depends on `all`; passing the same flags keeps it a no-op
        # rebuild instead of re-running with the default (broken) flags.
        # PREFIX=/ SBINDIR=/bin → binaries land in <package>/bin.
        self.run(
            f"make {self._make_vars()} install "
            f"DESTDIR={self.package_folder} PREFIX=/ SBINDIR=/bin LIBDIR=/lib "
            "-j1",
            cwd=self.source_folder,
        )

    def package_info(self):
        # iproute2 is a tool set, not a library.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
