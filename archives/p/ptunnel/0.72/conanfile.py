#!/usr/bin/env python3
"""Conan recipe — ptunnel 0.72 — plain Makefile CLI tool (no configure).

ptunnel (Ping Tunnel) tunnels TCP connections to a remote host over ICMP
echo request/reply ("ping") packets, via a client + proxy model. It is a
pcap-based command-line tool producing a single binary `ptunnel`.

Upstream: https://www.cs.uit.no/~daniels/PingTunnel/
Build system: plain Makefile — single binary `ptunnel`, links libpcap + pthread.

OHOS notes:
- plain Makefile with hardcoded CC=gcc; compile via `make CC=<clang>` and route
  libpcap paths through the Makefile's `CFLAGS` (include) and `LDOPTS` (lib),
  since its rules never reference CPPFLAGS/LDFLAGS (ptunnel.h includes <pcap.h>;
  libpcap installs headers under include/pcap/)
- links -lpcap (conan libpcap/1.10.6) and -lpthread (provided by OHOS libc)
- upstream `make install` uses plain GNU `install`; packaging is done manually
  in package() to avoid tool-call portability issues on OHOS
- upstream ships no upstream test target (see test_package/MANIFEST.yml); the
  packaged binary is functionally smoke-tested in test_package
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PtunnelConan(ConanFile):
    name = "ptunnel"
    version = "0.72"
    description = "Tunnel TCP connections over ICMP echo request/reply packets"
    license = "BSD-3-Clause"
    homepage = "https://www.cs.uit.no/~daniels/PingTunnel/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: explicit allow-list instead of == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ptunnel supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: compiler from Conan conf, never a bare env var
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        return compilers.get("c", "clang") if compilers else "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        pcap_pkg = self.dependencies["libpcap"].package_folder
        incdir = os.path.join(pcap_pkg, "include")
        libdir = os.path.join(pcap_pkg, "lib")
        # ptunnel.h includes <pcap.h>; libpcap installs pcap/pcap.h. The
        # Makefile's compile rule uses $(CFLAGS) and its link rule uses
        # $(LDOPTS) — it never references CPPFLAGS/LDFLAGS — so route the pcap
        # include dir into CFLAGS and the pcap lib dir into LDOPTS (before
        # -lpcap), keeping upstream's -Wall -g. Command-line make variables
        # override the Makefile's plain assignments (CC = gcc etc.).
        cflags = f"-Wall -g -I{incdir} -I{os.path.join(incdir, 'pcap')}"
        ldopts = f"-L{libdir} -lpthread -lpcap"
        # -j1 (R9): parallel make relies on a jobserver fifo, broken on HMDFS.
        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" LDOPTS="{ldopts}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man8")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)
        # manual install: upstream `make install` relies on coreutils `install`
        exe_dst = os.path.join(bindir, "ptunnel")
        shutil.copy2(os.path.join(src, "ptunnel"), exe_dst)
        os.chmod(exe_dst, 0o755)
        shutil.copy2(os.path.join(src, "ptunnel.8"),
                     os.path.join(mandir, "ptunnel.8"))
        copy(self, "LICENSE", src=src,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # ptunnel is a CLI tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
