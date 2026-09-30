#!/usr/bin/env python3
"""Conan recipe for memstat 1.2 — identify what is using up virtual memory.

memstat is a small (396 line) POSIX C tool that walks /proc/<pid>/maps and
reports how much virtual address space every process and every shared object
is mapped.  It builds from a hand-written 4-target Makefile (no autotools,
no cmake) and has no third-party dependencies — libc only.

OHOS adaptation (see patches/0001-memstat-c-musl-strtol-errno-and-path-max.patch):

* ``PATH_MAX`` needs ``<limits.h>``: on glibc it arrives transitively, on the
  musl-based OHOS libc the declaration of the maps-line buffer fails and every
  later use of it cascades into "undeclared identifier".
* ``perm[4]`` is written through ``"%4s"``, which needs 5 bytes (4 + NUL);
  the OHOS toolchain flags it as ``-Wfortify-source``.
* ``read_proc()`` bailed out on ``errno != 0`` after
  ``strtol(ent->d_name, NULL, 10)``.  musl's strtol() sets EINVAL when the
  string has no digits, so the very first readdir() entry (".") killed the
  whole scan with ``strtol: Invalid argument`` and exit 1 — memstat could not
  report anything at all.  glibc leaves errno untouched there, which is why
  this is invisible upstream.

The test_package exercises the packaged binary on the real /proc, including
the ``-p <pid>`` path that regresses without the strtol fix.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class MemstatConan(ConanFile):
    name = "memstat"
    version = "1.2"
    description = "Identify what's using up virtual memory (/proc/<pid>/maps reporter)"
    license = "GPL-2.0"
    homepage = "https://salsa.debian.org/debian/memstat"
    url = "https://salsa.debian.org/debian/memstat"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        # R32: OHOS must be accepted alongside Linux, never compared with ==.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"memstat supports Linux and OHOS only, got {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Raw-make project: everything happens in source_folder, no cmake layout.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: the compiler comes from Conan conf, never from ${CC}/${CFLAGS}
        # shell variables (they are empty on the release worker and the build
        # would silently fall back to whatever is on PATH).  The ohos-aarch64
        # profile carries tools.build:compiler_executables as a dict, so read
        # it as a dict rather than as a ":c" sub-key.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        # The upstream Makefile does `CFLAGS += -g -Wall -O2`.  A variable set
        # on the make command line overrides the in-Makefile `+=`, so passing
        # CFLAGS explicitly is what actually controls the flags.  -O2 -Wall
        # reproduces the upstream optimisation level without the -g debug
        # payload in a Release package.
        # R9: -j1, never -j$(nproc).
        self.run(f"make CC={cc} CFLAGS='-O2 -Wall' -j1")

    def package(self):
        copy(self, "memstat", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        # Upstream installs memstat.conf under $(DESTDIR)/etc; memstat only
        # reads it when a mapping has no path and inode resolution is needed.
        copy(self, "memstat.conf", self.source_folder,
             os.path.join(self.package_folder, "etc"))
        copy(self, "memstat.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # Application package: expose bin/ and declare the (empty) library
        # layout explicitly rather than leaving it implicit.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
