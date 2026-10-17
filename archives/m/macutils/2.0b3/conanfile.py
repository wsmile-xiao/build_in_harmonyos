#!/usr/bin/env python3
"""Conan recipe for macutils 2.0b3 — Macintosh file-format conversion tools.

macutils (Dik T. Winter, 1992; Debian 2.0b3-16 source as kept in the
dgilman/macutils repository) ships seven command-line tools: macunpack,
hexbin, binhex, macsave, macstream, tomac and frommac.

Build system: hand-written recursive makefiles (no configure). The top-level
makefile only forwards the feature macros in `CF`; `CC`/`AR`/`CC_FOR_BUILD`
given on the make command line reach the sub-makes through MAKEFLAGS.

Adaptation points (see notes.md):
- K&R C (implicit int, old-style definitions): compiled as `-std=gnu89`.
- crc/makecrc is a build-time generator that must run on the build machine:
  patch 0004 replaces the hard-coded `cc`/`ar` with `$(CC_FOR_BUILD)`/`$(AR)`;
  it is linked statically so it runs both on the AArch64 CI worker and on an
  x86_64 runner through qemu-user binfmt.
- musl provides neither MAXNAMLEN nor DIRSIZ (patch 0005, NAME_MAX fallback).
- missing prototypes of pointer-returning helpers (patches 0001-0003).
- built without -DBSD: the BSD branch links rindex(), absent from the OHOS
  libc.so export table.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class MacutilsConan(ConanFile):
    name = "macutils"
    version = "2.0b3"
    description = ("Macintosh file conversion tools: macunpack (StuffIt/PackIt/"
                   "Compactor... archives), hexbin/binhex (BinHex 4.0), "
                   "macsave/macstream (MacBinary), tomac/frommac (XMODEM)")
    # README: "use and redistribution of all such code is explicitly allowed.
    # For some parts of it the GNU software license does apply."
    license = "LicenseRef-macutils-README"
    homepage = "https://github.com/dgilman/macutils"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _TOOLS = (
        "macunpack/macunpack",
        "hexbin/hexbin",
        "binhex/binhex",
        "mixed/macsave",
        "mixed/macstream",
        "comm/tomac",
        "comm/frommac",
    )
    # Feature macros from the upstream top-level makefile (CF = ...) minus
    # -DBSD ("if you are on a BSD system"): under BSD hexbin resolves
    # search_last to rindex(), which the OHOS libc.so does not export (only
    # libc.a has it) -> "ld.lld: error: undefined symbol: rindex". The
    # non-BSD branches use strrchr()/<time.h>/memcpy()/memset().
    _UPSTREAM_CF = "-DTYPES_H -DDIRENT_H -DTERMIOS_H -DNODOT -DAPPLEDOUBLE"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # The makefiles reference sibling directories (../crc, ../util,
        # ../fileio) and have no VPATH support: build in-source.
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _cc(self):
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        return executables.get("c") or "clang"

    def _ar(self, cc):
        # llvm-ar sits next to the clang driver (/data/service/hnp/bin on the
        # worker) or next to the resolved NDK binary when clang is a symlink.
        for folder in (os.path.dirname(cc), os.path.dirname(os.path.realpath(cc))):
            candidate = os.path.join(folder, "llvm-ar")
            if folder and os.path.isfile(candidate):
                return candidate
        return shutil.which("llvm-ar") or "ar"

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        flags = ["-std=gnu89", "-Wno-deprecated-non-prototype", self._UPSTREAM_CF]
        flags += self.conf.get("tools.build:cflags", default=[], check_type=list)
        flags += self.conf.get("tools.build:exelinkflags", default=[], check_type=list)
        make_vars = [
            f"CC={cc}",
            f"AR={self._ar(cc)}",
            f"CC_FOR_BUILD={cc} -static",
            f"CF={' '.join(flags)}",
        ]
        # Recursive makefiles with cross-directory prerequisites: serial make.
        self.run("make " + " ".join(shlex.quote(v) for v in make_vars),
                 cwd=self.source_folder)
        # Upstream ships no test suite (makefile targets: all/clean/clobber/
        # lint/install/distr only); functional coverage is in test_package/.

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        for tool in self._TOOLS:
            copy(self, os.path.basename(tool), src=os.path.join(src, os.path.dirname(tool)),
                 dst=bindir)
            os.chmod(os.path.join(bindir, os.path.basename(tool)), 0o755)
        copy(self, "*.1", src=os.path.join(src, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "README", src=src, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
