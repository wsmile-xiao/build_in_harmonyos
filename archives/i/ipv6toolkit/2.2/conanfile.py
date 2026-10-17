#!/usr/bin/env python3
"""Conan recipe — ipv6toolkit 2.2 (Makefile, IPv6 security assessment tools).

Builds 16 C tools (addr6/scan6/frag6/icmp6/etc.) and 2 shell scripts
(blackhole6/messi) plus 1 Perl script (script6) using the upstream
GNUmakefile. Patch 0001 uses POSIX feature detection (_SYS_SOCKET_H)
to avoid a sockaddr_storage redefinition conflict between linux/socket.h
and sys/socket.h on OHOS musl, without platform-specific macros (R8).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Ipv6toolkitConan(ConanFile):
    name = "ipv6toolkit"
    version = "2.2"
    description = "SI6 Networks IPv6 security assessment toolkit (addr6, scan6, frag6, etc.)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.si6networks.com/research/tools/ipv6toolkit/"
    url = "https://github.com/fgont/ipv6toolkit"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

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

        # libpcap include/lib paths from Conan dependency.
        pcap_info = self.dependencies["libpcap"].cpp_info
        pcap_inc = " ".join(f"-I{d}" for d in pcap_info.includedirs)
        pcap_lib = " ".join(f"-L{d}" for d in pcap_info.libdirs)

        cflags = "-Wall -Wno-address-of-packed-member -Wno-missing-braces -fPIC -O2"
        ldflags = f"{pcap_lib} -lpcap -lm"

        # R9: always -j1.
        self.run(f'make -C "{self.source_folder}" -j1 CC="{cc}" '
                  f'CFLAGS="{cflags}" CPPFLAGS="{pcap_inc}" '
                  f'LDFLAGS="{ldflags}"')

    def package(self):
        src = self.source_folder
        dst = self.package_folder

        # addr6 → bin/
        copy(self, "addr6", src=src,
             dst=os.path.join(dst, "bin"), keep_path=False)

        # sbin tools (16 C programs + 2 shell scripts + 1 Perl script)
        sbin_tools = [
            "flow6", "frag6", "icmp6", "jumbo6", "mldq6",
            "na6", "ni6", "ns6", "path6", "ra6",
            "rd6", "rs6", "scan6", "tcp6", "udp6",
            "blackhole6", "messi", "script6",
        ]
        for tool in sbin_tools:
            copy(self, tool, src=src,
                 dst=os.path.join(dst, "sbin"), keep_path=False)

        # Data files (OUI/port/country/DNS databases)
        copy(self, "*", src=os.path.join(src, "data"),
             dst=os.path.join(dst, "share", "ipv6toolkit"), keep_path=False)

        # Man pages
        copy(self, "*.1", src=os.path.join(src, "manuals"),
             dst=os.path.join(dst, "share", "man", "man1"), keep_path=False)
        copy(self, "*.7", src=os.path.join(src, "manuals"),
             dst=os.path.join(dst, "share", "man", "man7"), keep_path=False)
        copy(self, "*.5", src=os.path.join(src, "manuals"),
             dst=os.path.join(dst, "share", "man", "man5"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
