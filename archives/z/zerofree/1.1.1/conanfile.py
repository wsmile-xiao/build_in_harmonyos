#!/usr/bin/env python3
"""Conan recipe — zerofree 1.1.1 (zero the unallocated blocks of an ext2/3/4 fs).

zerofree rewrites the *free* blocks of an ext2/3/4 filesystem so that the
resulting image compresses well / can be sparsified (the usual use case is
"shrink a VM disk image").  Upstream is a single C file plus a plain GNU-Make
Makefile — no configure, no autotools.

OHOS notes:

  * ``Makefile`` hard-codes ``CC=gcc`` and its only rule links with
    ``$(CC) $(CFLAGS) -o zerofree zerofree.c -lext2fs``, so a cross toolchain
    can neither override the compiler nor inject ``-I``/``-L`` for the
    dependency.  Patch 0001 makes CC overridable and routes
    ``$(CPPFLAGS)``/``$(LDFLAGS)``/``$(LDLIBS)`` through the rule (the same
    generic-Makefile fix used by the no-more-secrets recipe).  ``-lext2fs`` is
    deliberately kept *after* ``$(LDFLAGS)`` and *before* ``$(LDLIBS)`` so that
    static-link order stays correct.

  * libext2fs is taken from the already-published ``e2fsprogs`` package
    (component ``ext2fs``), so this package does not carry its own copy of
    e2fsprogs.  ``e2fsprogs`` builds static by default; ``-lcom_err`` and
    ``-luuid`` are required to close the static link.

  * GNU coreutils ``install`` is not available in the OHOS build sandbox, so
    ``package()`` copies the produced binary directly instead of calling
    ``make install`` (upstream has no install target anyway).

License: GPL-2.0-or-later
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ZerofreeConan(ConanFile):
    name = "zerofree"
    version = "1.1.1"
    description = ("zerofree - zeroes the unallocated blocks of an ext2/3/4 "
                   "filesystem in place so that the image compresses or "
                   "sparsifies well")
    license = "GPL-2.0-or-later"
    homepage = "https://frippery.org/uml/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("filesystem", "ext2", "ext3", "ext4", "sparse", "vm", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libext2fs lives in the already-published e2fsprogs package.
        self.requires("e2fsprogs/1.47.4")

    def layout(self):
        # Upstream is a plain in-source Makefile (no VPATH), so keep source,
        # build and generators in the same folder.
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: the compiler must come from the Conan toolchain, never from an
        # undefined shell variable (empty on release workers).
        comp = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}
        cc = comp.get("c") or os.environ.get("CC") or "clang"

        e2fs_pkg = self.dependencies["e2fsprogs"].package_folder
        inc = os.path.join(e2fs_pkg, "include")
        lib = os.path.join(e2fs_pkg, "lib")

        self.run(
            f'make -j1 CC={cc} '
            f'CPPFLAGS="-I{inc}" '
            f'CFLAGS="-std=gnu99 -O2 -Wall -Wextra" '
            f'LDFLAGS="-L{lib}" '
            f'LDLIBS="-lcom_err -luuid"'
        )

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "zerofree", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # CLI package: expose bin/ so consumers get it on PATH via VirtualRunEnv.
        self.cpp_info.bindirs = ["bin"]
