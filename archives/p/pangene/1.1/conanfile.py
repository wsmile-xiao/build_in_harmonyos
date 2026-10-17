#!/usr/bin/env python3
"""Conan recipe — pangene 1.1 (pangenome gene graph constructor).

pangene is a pure-C CLI tool by Heng Li (lh3) that constructs a pangenome
gene graph in GFA format from miniprot PAF alignments of a protein set
against multiple genomes.  Upstream ships a plain Makefile with no
configure step and no install rule: `make` builds the single `pangene`
executable.

Structure mirrors the sibling recipe miniprot/0.18 (same author, same
Makefile + vendored klib + zlib pattern, zero patches needed):
  - CC is taken from Conan conf (R33), never from shell env vars.
  - The Makefile's default LIBS="-lpthread -lz -lm" is overridden so -lz
    resolves against the Conan zlib package, not the sysroot (R26).
  - package() copies the single user-facing artifact `pangene` into bin/.

Upstream has no formal test target (no make test / make check, see
notes.md and test_package/MANIFEST.yml).  The README quick-start
(`pangene test/C4/*.paf.gz > C4.gfa`) is re-implemented in test_package/
with the upstream C4 fixtures.
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class PangeneConan(ConanFile):
    name = "pangene"
    version = "1.1"
    description = ("pangene — construct a pangenome gene graph from "
                   "miniprot alignments")
    license = "MIT"
    homepage = "https://github.com/lh3/pangene"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # read.c KSTREAM_INIT + kseq.h include <zlib.h>; upstream links -lz.
        # R26: the zlib symbols come from the Conan package, not the sysroot.
        self.requires("zlib/1.3.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: get compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"

        # Replace Makefile's default LIBS="-lpthread -lz -lm" so that -lz
        # resolves to the static zlib in the Conan package, not a sysroot one.
        zlib = self.dependencies["zlib"]
        zlib_libdir = zlib.cpp_info.libdirs[0]
        libs = "-lpthread -L{} -lz -lm".format(zlib_libdir)

        # Zero-patch build: upstream CFLAGS (-std=c99 -g -Wall -O2) unchanged.
        # basic_layout: self.run() executes in the build folder; the Makefile
        # lives in the source folder, so drive make with -C. R9: -j1.
        self.run('make -C "{}" CC="{}" LIBS="{}" -j1'.format(
            self.source_folder, cc, libs))

    def package(self):
        # Upstream has no install rule; the single user-facing artifact is
        # the `pangene` executable.
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "pangene", self.source_folder, bindir, keep_path=False)
        os.chmod(os.path.join(bindir, "pangene"), 0o755)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
