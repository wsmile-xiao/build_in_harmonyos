#!/usr/bin/env python3
"""Conan recipe — miniprot 0.18 (protein-to-genome aligner).

miniprot is a pure-C CLI tool that maps a protein sequence against a genome
while considering splicing (introns) and frameshifts.  Upstream ships a plain
Makefile with no configure step and no install rule: `make` builds the
`miniprot` executable plus the static libminiprot.a from the same objects.

Upstream has no formal test target (no make test / make check — verified,
see notes.md and test_package/MANIFEST.yml).  The upstream-equivalent
verification (build + README quick-start on test/DPP3 fixtures) was executed
with the OHOS AArch64 toolchain and re-implemented from the installed
package in test_package/.
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class MiniprotConan(ConanFile):
    name = "miniprot"
    version = "0.18"
    description = ("miniprot — aligns proteins to genomes with splicing, "
                   "frameshifts and rearrangements")
    license = "MIT"
    homepage = "https://github.com/lh3/miniprot"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # bseq/index/ntseq kseq readers include <zlib.h>; upstream links -lz.
        # R26: the system-name lib comes from Conan, not the OHOS sysroot.
        self.requires("zlib/1.3.1")

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

        # Zero-patch build: upstream CFLAGS (-std=c99 -g -Wall -O3) unchanged.
        # basic_layout: self.run() executes in the build folder; the Makefile
        # lives in the source folder, so drive make with -C.
        self.run('make -C "{}" CC="{}" LIBS="{}" -j1'.format(
            self.source_folder, cc, libs))

    def package(self):
        # Upstream has no install rule; the single user-facing artifact is
        # the `miniprot` executable (libminiprot.a is an internal build
        # detail, not installed by upstream either).
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "miniprot", self.source_folder, bindir, keep_path=False)
        os.chmod(os.path.join(bindir, "miniprot"), 0o755)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
