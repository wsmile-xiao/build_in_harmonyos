#!/usr/bin/env python3
"""Conan recipe — ndppd 0.2.6

NDP Proxy Daemon — proxies Neighbor Discovery messages (Neighbor
Solicitation / Neighbor Advertisement) so that prefixes routed to a
different interface can be answered on the local link.

Upstream: https://github.com/DanielAdolfsson/ndppd
Build system: plain Makefile (no configure script).
License: GPL-3.0-or-later
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class NdppdConan(ConanFile):
    name = "ndppd"
    version = "0.2.6"
    description = "NDP Proxy Daemon — IPv6 Neighbor Discovery proxy for Linux"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/DanielAdolfsson/ndppd"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Default build path (no WITH_ND_NETLINK) has zero external
        # dependencies: standard C++ library + POSIX/libc only.
        # The optional libnl/glib path is intentionally NOT enabled.
        pass

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        # R33: get compiler from Conan conf (never bare shell env vars).
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp_execs.get("cxx") or "clang++"

        # Only build the `ndppd` binary target — the default `all` target
        # also builds gzipped man pages via hard-coded GZIP=/bin/gzip,
        # which does not exist on OHOS. Man pages are not packaged anyway.
        #
        # Default build path (no WITH_ND_NETLINK) compiles 9 .cc files and
        # needs no libnl/glib; the netlink monitor (which uses
        # pthread_cancel, unavailable on musl/OHOS) is guarded by
        # #ifdef WITH_ND_NETLINK and stays out of the build.
        cxxflags = "-O2 -fPIC -Wall"
        apply_conandata_patches(self)
        self.run(f'make -j1 ndppd CXX="{cxx}" CXXFLAGS="{cxxflags}"',
                 cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "ndppd", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "ndppd.conf-dist", src=self.source_folder,
             dst=os.path.join(self.package_folder, "res"), keep_path=False)

    def package_info(self):
        # Command-line daemon, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
