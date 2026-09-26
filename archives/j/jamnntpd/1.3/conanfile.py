#!/usr/bin/env python3
"""Conan recipe for JamNNTPd 1.3 — NNTP server for FidoNet JAM messagebases."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class JamnntpdConan(ConanFile):
    name = "jamnntpd"
    version = "1.3"
    description = (
        "JamNNTPd is an NNTP server that allows newsreaders to access a JAM "
        "messagebase (FidoNet/FTN areas). Ships the jamnntpd daemon and the "
        "makechs charset-table generator."
    )
    license = ("LGPL-2.1-or-later", "LicenseRef-jamnntpd")
    homepage = "https://ftnapps.sourceforge.net/jamnntpd.html"
    url = ""  # CI fills this
    topics = ("nntp", "fidonet", "jam", "messagebase", "server")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jamnntpd only supports Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "src")
        cc_executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = cc_executables.get("c", "") if isinstance(cc_executables, dict) else ""
        # E540 family: the shared CI profile hardcodes /data/service/hnp/bin/clang,
        # which exists on CI workers but not on this device. Never trust a conf
        # path blindly — fall back to PATH discovery (device keeps its OHOS clang
        # wrapper in ~/usr/local/bin, which is on PATH via the profile buildenv).
        if not cc or not os.path.isfile(cc) or not os.access(cc, os.X_OK):
            cc = (shutil.which("aarch64-unknown-linux-ohos-clang")
                  or shutil.which("clang") or shutil.which("gcc"))
        if not cc:
            raise ConanException("no usable C compiler found (conf path dead, none on PATH)")
        ar = shutil.which("llvm-ar") or shutil.which("ar")
        ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib")
        if not ar or not ranlib:
            raise ConanException("need ar and ranlib (llvm-ar/llvm-ranlib) on PATH")

        # Upstream has no automated test entry (N_static=0): invoke the test
        # target anyway so the build log carries the verbatim make error.
        self.run("make -f Makefile.linux check", cwd=src, env=None, ignore_errors=True)

        # OHOS/musl adaptations, flags only (no source patch):
        # -Ulinux: jam.h typedefs ushort/ulong/uchar itself unless `linux` is
        #   defined (glibc exposes ulong via sys/types.h, musl does not).
        # -include fcntl.h: OHOS sys/file.h is a minimal BSD header that does
        #   not pull in fcntl.h, but jamlib mbase.c needs struct flock/F_WRLCK.
        # Command-line variable overrides propagate into the jamlib sub-make
        # through MAKEFLAGS; jamlib still gets -D__LINUX__ from our CC string.
        self.run(
            f'make -C jamlib -f Makefile.linux CC="{cc} -D__LINUX__ -Ulinux -include fcntl.h -Wall" '
            f'AR="{ar} rcu"',
            cwd=src,
            env=None,
        )
        self.run(f'{ranlib} jamlib/jamlib.a', cwd=src, env=None)
        # STRIP=":" keeps the link-time ELF code signature added by the OHOS
        # clang wrapper intact (a later strip would invalidate it).
        self.run(f'make -f Makefile.linux CC="{cc} -Ulinux -Wall" STRIP=":"', cwd=src, env=None)

    def package(self):
        src = os.path.join(self.source_folder, "src")
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "jamnntpd", src, bindir)
        copy(self, "makechs", src, bindir)
        resxlat = os.path.join(self.package_folder, "res", "xlat")
        copy(self, "*.chs", os.path.join(self.source_folder, "xlat"), resxlat)
        copy(self, "*.chs", os.path.join(self.source_folder, "unicode", "xlat"),
             os.path.join(resxlat, "unicode"))
        copy(self, "jamnntpd.*", os.path.join(self.source_folder, "examples"),
             os.path.join(self.package_folder, "res", "examples"))
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE", os.path.join(src, "jamlib"), os.path.join(licenses, "jamlib"))
        copy(self, "ReadMe.txt", self.source_folder, licenses)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
