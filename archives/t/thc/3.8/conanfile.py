#!/usr/bin/env python3
"""Conan recipe — thc 3.8 (THC IPv6 Attack Toolkit, upstream thc-ipv6 v3.8).

Builds the thc-ipv6-lib packet factory (.o) plus 68 C tools (parasite6,
alive6, thcping6, fake_router6, ...) and the helper .sh/.pl scripts, using the
upstream hand-written Makefile. OHOS / musl adaptations:

* R33: CC is taken from Conan conf (tools.build:compiler_executables), never
  from a shell env var; defaults to the OHOS clang path.
* -march=native / -flto are removed via patch 0001 (illegal on OHOS clang).
* -lresolv / -lrt are removed via patch 0001 (musl has them inside libc).
* openssl / libpcap / libnetfilter_queue include+lib dirs are injected through
  CPPFLAGS / LDFLAGS; HAVE_SSL=yes (default) keeps -D_HAVE_SSL enabled.
* make is invoked with MANPAGES= so the `all` target does NOT run each binary
  to render its man page (the %.8 rule executes the tool — unsafe cross-build).
* R8: no __OHOS__ platform macro anywhere. Any sockaddr_storage conflict that
  surfaces under musl is fixed with feature detection (see notes.md).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ThcConan(ConanFile):
    name = "thc"
    version = "3.8"
    description = "THC IPv6 Attack Toolkit (parasite6, alive6, thcping6, fake_router6, ...)"
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/vanhauser-thc/thc-ipv6"
    url = "https://github.com/vanhauser-thc/thc-ipv6"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")
        self.requires("openssl/3.5.6")
        self.requires("libnetfilter_queue/1.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "/data/service/hnp/bin/clang")

        # Dependency include/lib paths (musl needs explicit -I/-L).
        pcap = self.dependencies["libpcap"].cpp_info
        ssl = self.dependencies["openssl"].cpp_info
        nfq = self.dependencies["libnetfilter_queue"].cpp_info
        cppflags = " ".join(f"-I{d}" for d in pcap.includedirs + ssl.includedirs + nfq.includedirs)
        ldflags = " ".join(f"-L{d}" for d in pcap.libdirs + ssl.libdirs + nfq.libdirs)
        # CRITICAL: command-line LDFLAGS *overrides* the Makefile's
        # `LDFLAGS += -lpcap -lssl -lcrypto` (GNU make command-line precedence),
        # so the Makefile's append is dropped and pcap/ssl symbols go unresolved.
        # Pass the actual -l libs ourselves so the linker line carries them.
        libs = " ".join(f"-l{lib}" for lib in pcap.libs + ssl.libs + nfq.libs)
        ldflags = f"{ldflags} {libs}".strip()

        # -march=native/-flto already removed by patch 0001.
        cflags = "-O2 -fPIC -Wall"

        # R9: always -j1. MANPAGES= avoids executing each binary for man pages.
        self.run(f'make -C "{self.source_folder}" -j1 MANPAGES= CC="{cc}" '
                  f'CFLAGS="{cflags}" CPPFLAGS="{cppflags}" '
                  f'LDFLAGS="{ldflags}"')

    def package(self):
        src = self.source_folder
        dst = self.package_folder
        bin_dir = os.path.join(dst, "bin")

        # Copy every built executable (skip source/build artifacts AND helper
        # scripts — only ship the real compiled tools).
        skip_ext = (".c", ".h", ".o", ".a", ".so", ".8", ".sh", ".pl")
        for name in os.listdir(src):
            fp = os.path.join(src, name)
            if not os.path.isfile(fp):
                continue
            if name.endswith(skip_ext):
                continue
            if os.access(fp, os.X_OK):
                copy(self, name, src=src, dst=bin_dir, keep_path=False)

        # Man page (pre-existing in source tree; generated ones are disabled by MANPAGES=).
        man = os.path.join(src, "thc-ipv6.8")
        if os.path.exists(man):
            copy(self, "thc-ipv6.8", src=src,
                 dst=os.path.join(dst, "share", "man", "man8"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
