#!/usr/bin/env python3
"""Conan recipe — rtapd 1.7 (plain Makefile, C).

rtapd is the TAP/TNPP paging daemon of the rtnppd suite.  It receives TNPP
packets from the external queue (rtnppd) over an AF_UNIX datagram socket,
reassembles the TAP page blocks they carry, looks the pager address up in a
route table and delivers the page to a serial modem, a file, a filter program
or another TNPP address.  The tarball also builds `vsnppd` (a small SNPP/TNPP
gate) and ships the `*.filter.rtapd` / `*.pl` helper scripts.

Build system: plain Makefile, no configure.  The upstream Makefile keeps every
SQL backend (mSQL/PostgreSQL/MySQL) commented out and `LIBS` empty, so the
default build has no external dependency at all; we deliberately keep that
default (no `-DUSE_POSTGRESQL`) so the package needs no database client.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RtapdConan(ConanFile):
    name = "rtapd"
    version = "1.7"
    description = ("TAP/TNPP paging daemon: routes TNPP page packets coming from "
                   "rtnppd to modems, files, filters or another TNPP address")
    license = "BSD-2-Clause"
    homepage = "https://sourceforge.net/projects/rtnppd/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rtapd supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: take the compiler from the Conan toolchain, never from shell env.
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"
        # The upstream Makefile hardcodes `CC` usage but no compiler value, and
        # `make install` wants root (mkdir /var/spool/psheduler), so package()
        # copies the built binaries instead of running `make install`.
        self.run(f"make -j1 CC='{cc}' CFLAGS='-O2 -pipe -g'", cwd=self.source_folder)

    def package(self):
        copy(self, "COPYRIGHT", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "rtapd", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "vsnppd", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
