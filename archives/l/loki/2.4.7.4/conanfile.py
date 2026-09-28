#!/usr/bin/env python3
"""Conan recipe for loki 2.4.7.4 (Simon Heath) - MCMC multivariate linkage analysis.

Upstream is a 2003-era C program with a *generated* autotools tree (configure +
Makefile.in + pre-generated flex/bison parsers). It builds four programs:
`loki`, `prep`, `qavg`, `hist`.

OpenHarmony/clang adaptations (see notes.md):
* ``configure``/``config.status`` run under ``umask 077``; HMDFS (the writable
  HomeArea) does not honour that mode, so config.status cannot create its temp
  files. Rewrite the umask to 022 before configuring.
* The code relies on gcc's default ``-fcommon`` (tentative definitions such as
  ``MMsg``/``FMsg``/``int strip_vars`` colliding under clang's ``-fno-common``).
  Pass ``CFLAGS=-fcommon`` to configure.
* ``AR``/``RANLIB`` are detected as the GNU names; the OHOS toolchain only ships
  ``llvm-ar``/``llvm-ranlib``, so pass them explicitly.
* The pre-generated flex/bison sources (``param_lex.c``/``param_parse.c``) mean
  bison/flex are not required at build time.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout

PROGRAMS = ["loki", "prep", "qavg", "hist"]


class LokiConan(ConanFile):
    name = "loki"
    version = "2.4.7.4"
    description = "MCMC multivariate linkage analysis on general pedigrees"
    license = "GPL-2.0-or-later"
    homepage = "https://www.stat.washington.edu/thompson/Genepi/loki.shtml"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # HMDFS ignores the mode bits of mktemp dirs created under `umask 077`.
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = str(cc.get("c") or "clang")
        bindir = os.path.dirname(cc)
        self.run(
            f'CC="{cc}" CFLAGS="-g -O2 -fcommon" '
            f'AR="{bindir}/llvm-ar" RANLIB="{bindir}/llvm-ranlib" ./configure',
            cwd=self.source_folder,
        )
        self.run(
            f'make -j1 AR="{bindir}/llvm-ar" RANLIB="{bindir}/llvm-ranlib"',
            cwd=self.source_folder,
        )
        # Run the upstream test suite (7 statistical regression tests). The
        # upstream `tests` target ignores failures, so run each test target and
        # assert its result: capture make's stdout, then require exactly 7 "OK"
        # lines and no "Failed".
        log = os.path.join(self.build_folder, "loki-upstream-tests.log")
        self.run(
            f'make -j1 -B tests '
            f'AR="{bindir}/llvm-ar" RANLIB="{bindir}/llvm-ranlib" '
            f'2>&1 | tee "{log}"',
            cwd=self.source_folder,
        )
        self.run(
            f'ok=$(grep -cE "\\.\\.\\. OK$" "{log}"); '
            f'bad=$(grep -cE "\\.\\.\\. Failed$" "{log}"); '
            f'echo "upstream tests: ok=$ok failed=$bad"; '
            f'[ "$ok" -eq 7 ] && [ "$bad" -eq 0 ]',
            cwd=self.source_folder,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for prog in PROGRAMS:
            src = self._find_program(prog)
            copy(self, prog, src=src, dst=bin_dir, keep_path=False)
            os.chmod(os.path.join(bin_dir, prog), 0o755)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share/doc/loki"), keep_path=False)

    def _find_program(self, name):
        for sub in ("lokisrc", "prepsrc", "utils"):
            if os.path.isfile(os.path.join(self.source_folder, sub, name)):
                return os.path.join(self.source_folder, sub)
        return self.source_folder

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
