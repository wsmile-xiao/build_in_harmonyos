#!/usr/bin/env python3
"""Conan recipe for netselect 0.4 — ultrafast parallel ping (single-file C, Makefile).

Build: make CC=<conan compiler> -j1 (netselect.c is the only source).
Upstream install target chown's root and sets setuid; NOT usable under Conan —
package() copies the binary and man page by hand instead.

Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NetselectConan(ConanFile):
    name = "netselect"
    version = "0.4"
    description = (
        "netselect — an ultrafast implementation of ping that measures "
        "network latency to multiple hosts in parallel using ICMP/UDP raw sockets"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/apenwarr/netselect"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # no third-party deps: libc only (raw sockets)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compiler from Conan conf, never from bare shell env vars.
        # The upstream Makefile hardcodes `CC = gcc`; a command-line CC= wins.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # Drop `-I.` from CFLAGS: upstream ships fallback netinet/{ip,ip_icmp,udp}.h
        # (old BSD types u_char/u_short) that shadow the musl/OHOS sysroot headers
        # (n_short etc.) and fail with ~20 unknown-type errors (E113 family).
        # The system headers define the same structs with portable types.
        # musl does not provide the legacy BSD typedefs u_char/u_short used by
        # netselect.c itself (seq/ttl/cksum fields) — map them to stdint types
        # via -D macros (E113 add-cflags approach, no source patch needed).
        # Drop `-g` as well: DWARF embeds the build directory path, which trips
        # the OHOS host-path-leak check (T2 of test_ohos).
        cflags = "-O2 -Wall -g0 -Du_char=uint8_t -Du_short=uint16_t"
        # R9: always -j1
        self.run(f"make CC={cc} CFLAGS={cflags!r} -j1", cwd=self.source_folder)

    def package(self):
        # Upstream `make install` does chown root + chmod u+s (setuid) and uses
        # `install -o root`; those steps are wrong for Conan packaging (and
        # E087: HMDFS has no execute-permission semantics to rely on anyway).
        # Copy artifacts manually instead — same layout as the FreeBSD port:
        # bin/netselect + share/man/man1/netselect.1. netselect-apt is a perl
        # script with a hard /etc/debian-read lists assumption; not shipped.
        copy(self, "netselect", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "netselect.1", self.source_folder, os.path.join(self.package_folder, "share/man/man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
