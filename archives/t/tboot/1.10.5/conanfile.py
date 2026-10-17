#!/usr/bin/env python3
"""Conan recipe — tboot 1.10.5 (Intel TXT measured-launch tooling).

Upstream tboot is built from a hand-written, multi-level GNU make tree.  Six
sub-projects hang off the top-level Makefile:

  * ``tboot``         — the freestanding x86-32 boot module (Measured Launch
                        Environment).  ``tboot/Config.mk`` hard-codes
                        ``-m32 -march=i686`` and ``LDFLAGS = -melf_i386``; it
                        is Intel TXT / x86 firmware and cannot be produced for
                        an aarch64 target.
  * ``safestringlib`` — portable C bounded-string library (built in-tree, not
                        shipped as a third-party dependency).
  * ``lcptools-v2``   — LCP policy tools (``lcp2_mlehash``, ``lcp2_crtpol``,
                        ``lcp2_crtpollist``, ``lcp2_crtpolelt``).
  * ``tb_polgen``     — Verified Launch Policy generator.
  * ``utils``         — ``txt-stat`` / ``txt-parse_err`` (``txt-acminfo`` is
                        x86-only: it pokes MSRs and IO ports through
                        ``tboot/include/{processor,io}.h``).
  * ``docs``          — man pages.

This package therefore ships the seven portable host tools (plus their man
pages) for aarch64 OHOS; the x86-only ``tboot`` module and ``txt-acminfo`` are
excluded by patches 0002/0009 and recorded in notes.md.

The tools link ``-lcrypto`` and ``-lz`` (lcptools-v2/Makefile:69,
tb_polgen/Makefile:18), resolved against the Conan-provided OpenSSL 3.5.6.1 and
zlib 1.3.1.1.  Both are consumed as static archives here, so the executables
depend on nothing but libc at runtime.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# (sub-directory, executable) of every tool built on all targets.
TOOLS = (
    ("lcptools-v2", "lcp2_mlehash"),
    ("lcptools-v2", "lcp2_crtpol"),
    ("lcptools-v2", "lcp2_crtpollist"),
    ("lcptools-v2", "lcp2_crtpolelt"),
    ("tb_polgen", "tb_polgen"),
    ("utils", "txt-stat"),
    ("utils", "txt-parse_err"),
)


class TbootConan(ConanFile):
    name = "tboot"
    version = "1.10.5"
    description = ("Intel TXT measured-launch host tooling: lcptools-v2 policy "
                   "tools, tb_polgen and the txt-stat/txt-parse_err utilities")
    license = "BSD-3-Clause"
    homepage = "https://sourceforge.net/projects/tboot/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: the OHOS recipe must accept both Linux and OHOS platforms.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tboot host tools are only supported on Linux/OHOS, not {self.settings.os}")

    def requirements(self):
        # The two third-party libraries the upstream Makefiles link:
        # lcptools-v2 (lcputils.c uses the OpenSSL 3 provider API) and
        # tb_polgen need libcrypto; lcptools-v2/mlehash.c and
        # tb_polgen/commands.c additionally need zlib.
        self.requires("openssl/3.5.6.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # R33: toolchain and dependency paths come from Conan, never from bare
        # shell variables.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"

        includedirs, libdirs = [], []
        for dep in ("openssl", "zlib"):
            cpp_info = self.dependencies[dep].cpp_info.aggregated_components()
            includedirs.extend(cpp_info.includedirs)
            libdirs.extend(cpp_info.libdirs)

        # Config.mk and every sub-Makefile append to CFLAGS/LDFLAGS, so the
        # dependency paths are handed over as an environment prefix of the
        # make command itself: passing CFLAGS as a *command line* variable
        # would make make ignore those `+=` additions (notably
        # safestringlib's -Iinclude and utils' -D_LARGEFILE64_SOURCE).
        cflags = " ".join(f"-I{d}" for d in includedirs)
        ldflags = " ".join(f"-L{d}" for d in libdirs)
        # R9: -j1 (the build is small and the Makefiles are recursive).
        self.run(f'CFLAGS="{cflags}" LDFLAGS="{ldflags}" '
                 f"make CC={cc} AR={ar} RANLIB={ranlib} -j1",
                 cwd=self.source_folder)

    def package(self):
        for subdir, tool in TOOLS:
            copy(self, tool, os.path.join(self.source_folder, subdir),
                 os.path.join(self.package_folder, "bin"), keep_path=False)
        for _, tool in TOOLS:
            copy(self, f"{tool}.8", os.path.join(self.source_folder, "docs", "man"),
                 os.path.join(self.package_folder, "share", "man", "man8"),
                 keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # man8 pages are shipped in share/man/man8 (documentation resource dir).
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
