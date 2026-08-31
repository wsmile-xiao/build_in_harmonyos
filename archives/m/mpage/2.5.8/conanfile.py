#!/usr/bin/env python3
"""Conan recipe — mpage 2.5.8 (plain Makefile, no configure).

mpage reduces and prints multiple pages of text per sheet on a PostScript
compatible printer.  Builds from the official upstream tarball with the
project's hand-written Makefile (no autotools, no CMake).

Build system: plain Makefile.  The upstream Makefile hard-codes
``CC=gcc`` and ``CFLAGS=-O2 -s ...``; on OHOS the only adaptation needed
is a command-line ``CC=clang`` override plus ``PREFIX`` redirected to the
package folder.  No source files are modified (zero patches).

License: GPL-2.0-or-later
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MpageConan(ConanFile):
    name = "mpage"
    version = "2.5.8"
    description = "Print multiple pages of text per sheet on a PostScript compatible printer"
    license = "GPL-2.0-or-later"
    homepage = "https://www.mesa.nl/pub/mpage/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: os 判断必须 in ("Linux", "OHOS")，不能 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mpage supports Linux and OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("mpage supports only OHOS armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _src_dir(self):
        """Locate the real source root (the dir holding mpage.c + Makefile).

        The upstream tarball's top-level entries are prefixed with ``./``
        (``./mpage-2.5.8/...``), which defeats Conan 2.29.1's strip_root
        single-root detection on this OHOS-adapted conan, so the source
        ends up one level deep under source_folder. Walk down to find the
        directory that actually contains both ``Makefile`` and ``mpage.c``
        rather than depending on the strip_root outcome. Pure path
        discovery — no source file is modified.
        """
        root = self.source_folder
        for dirpath, _dirs, files in os.walk(root):
            if "Makefile" in files and "mpage.c" in files:
                return dirpath
        return root

    def build(self):
        # R33: resolve the C compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp_execs.get("c") or "clang"
        prefix = self.package_folder
        # Faithful to upstream Makefile; only override the compiler (upstream
        # hard-codes CC=gcc) and redirect PREFIX to the conan package folder.
        # The Makefile derives DEFS/CFLAGS/BINDIR/LIBDIR/MANDIR from PREFIX and
        # its own config vars, so passing them on the command line is sufficient
        # and avoids touching any source file.
        # -j1: the Makefile uses a single FIFO jobserver-less build path and
        # sequential .o -> link; parallel is unnecessary and -jN triggers
        # "jobserver mkfifo: Operation not permitted" on OHOS restricted mounts.
        src_dir = self._src_dir()
        self.run(
            f"make -j1 CC={cc} PREFIX=\"{prefix}\"",
            cwd=src_dir,
        )

    def package(self):
        # `make install` is non-DESTDIR: it installs into PREFIX (already the
        # package folder) and honors BINDIR=$(PREFIX)/bin, LIBDIR=$(PREFIX)/share,
        # MANDIR=$(PREFIX)/man/man1.  We install the binary, the man page and the
        # Encodings/ library by hand instead, because the upstream install target
        # uses bare `mkdir -p`/`cp` with no install -D and no DESTDIR support,
        # and leaves the share/man tree owned by the build uid.
        src = self._src_dir()
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        enc_dir = os.path.join(self.package_folder, "share", "mpage")
        lic_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(man_dir, exist_ok=True)
        os.makedirs(enc_dir, exist_ok=True)
        os.makedirs(lic_dir, exist_ok=True)
        copy(self, "mpage", src=src, dst=bin_dir)
        copy(self, "msample", src=src, dst=bin_dir)
        copy(self, "mpage.1", src=src, dst=man_dir)
        copy(self, "*", src=os.path.join(src, "Encodings"), dst=enc_dir)
        copy(self, "COPYING", src=src, dst=lic_dir, keep_path=False)
        copy(self, "Copyright", src=src, dst=lic_dir, keep_path=False)

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
