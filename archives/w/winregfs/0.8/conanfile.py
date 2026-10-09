#!/usr/bin/env python3
"""Conan recipe for winregfs 0.8 — Windows Registry FUSE filesystem.

Upstream: https://codeberg.org/jbruchon/winregfs (Jody Bruchon), tag v0.8.
Build system: a plain Makefile (no configure step). Produces two console tools:

  - mount.winregfs : FUSE filesystem that exposes a registry hive
  - fsck.winregfs  : registry hive integrity checker

OHOS adaptation (details in notes.md):
  - The OHOS libfuse package ships no ``fuse.pc``, so upstream's
    ``pkg-config fuse`` lookup yields nothing and ``fuse.h`` is not found.
    The Makefile is patched to honour ``FUSE_CFLAGS``/``FUSE_LDFLAGS`` so this
    recipe can inject the paths resolved from the Conan dependency.
  - OHOS musl libc does not export the POSIX thread cancellation API
    (pthread_cancel and friends) that libfuse.a references, so linking fails
    with "undefined symbol: pthread_cancel" (knowledge base E085). The patch
    adds ``pthread_compat.c`` and it is linked via ``BUILD_PTHREAD_COMPAT=1``.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class WinregfsConan(ConanFile):
    name = "winregfs"
    version = "0.8"
    description = "Windows Registry FUSE filesystem (mount.winregfs / fsck.winregfs)"
    license = "LGPL-2.1-only OR MIT"
    homepage = "https://codeberg.org/jbruchon/winregfs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # winregfs is written against the FUSE 2.x API (FUSE_USE_VERSION 26,
        # <fuse.h>), so it needs libfuse 2.x, not the incompatible 3.x API.
        self.requires("libfuse/2.9.9")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _abs_dirs(package_folder, paths):
        return [p if os.path.isabs(p) else os.path.join(package_folder, p) for p in paths]

    def build(self):
        apply_conandata_patches(self)

        dep = self.dependencies["libfuse"]
        cpp = dep.cpp_info.aggregated_components()
        inc_flags = " ".join(f"-I{p}" for p in self._abs_dirs(dep.package_folder, cpp.includedirs))
        lib_flags = " ".join(f"-L{p}" for p in self._abs_dirs(dep.package_folder, cpp.libdirs))

        # R33: take the compiler from the Conan conf, never from bare shell vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # R9: -j1 (HMDFS forbids make's -j jobserver FIFO).
        # CFLAGS drops upstream's "-g": shipping debug info would embed the
        # build machine's absolute path (comp_dir) into the binaries.
        self.run(
            f'make CC={cc} -j1 '
            f'CFLAGS="-O2" '
            f'FUSE_CFLAGS="{inc_flags}" '
            f'FUSE_LDFLAGS="{lib_flags}" '
            f'BUILD_PTHREAD_COMPAT=1',
            cwd=self.source_folder,
        )

    def package(self):
        # `make install` uses `install -o root -g root -s`, which cannot run as
        # a normal user, so the artefacts are placed explicitly instead.
        copy(self, "mount.winregfs", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "fsck.winregfs", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "*.8.gz", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "LICENSE-*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
