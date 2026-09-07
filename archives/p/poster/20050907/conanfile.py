#!/usr/bin/env python3
"""Conan recipe — poster 20050907 (plain Makefile, single-file C program).

poster is a PostScript scaling/tile-printing utility by Jos van Eijndhoven:
it magnifies a single-page PostScript input onto a large poster and tiles it
across multiple sheets (e.g. -p2x2A4), with cropmarks and overlap for easier
assembly. It reads PS from stdin (or a file) and writes PS to stdout.

The upstream tarball ships a minimal hand-written Makefile whose single build
rule hardcodes `gcc` (not `$(CC)`):
    poster: poster.c
        gcc $(CFLAGS) -o poster poster.c -lm
so `make CC=<cc>` is a no-op — verified: on OHOS (no gcc on PATH) it fails
with "make: gcc: No such file or directory" (Error 127). We rewrite the
hardcoded `gcc` to `$(CC)` in build() (plain sed on the unpacked Makefile)
and invoke make with `-e`, so the compiler and flags exported by the Conan
toolchain environment (AutotoolsToolchain / conanbuild, R33-compliant —
never bare shell vars in self.run) drive the build.

Upstream `make install` is also unusable (hardcoded `strip` + absolute
/usr/local/bin paths); package() stages the tree manually instead.

package_type is "application" (single CLI binary, no library), zero conan
requirements (libc + libm only, both provided by musl).
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PosterConan(ConanFile):
    name = "poster"
    version = "20050907"
    description = "poster — PostScript scaling/tiling utility: enlarge a PS page onto a poster and print it tiled on multiple sheets"
    license = "GPL-2.0"
    homepage = "https://ftp.debian.org/debian/pool/main/p/poster/"
    url = "https://ftp.debian.org/debian/pool/main/p/poster/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain is not used for configure (there is none); it is
        # still the canonical way to materialise CC/CFLAGS/LDFLAGS into the
        # conanbuild environment for a plain-Makefile project (R33).
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        with chdir(self, src):
            # Upstream Makefile rule hardcodes `gcc` (not $(CC)), so a make
            # CC override is ineffective (verified: Error 127 on OHOS where
            # gcc does not exist). Rewrite the rule to honour $(CC), then let
            # make -e pick up CC/CFLAGS/LDFLAGS from the conanbuild
            # environment materialised by AutotoolsToolchain (R33).
            self.run("sed -i 's/^\\tgcc /\\t$(CC) /' Makefile")
            # Run make in the source dir (basic_layout's default build folder
            # has no Makefile). -e: toolchain CC/CFLAGS override the
            # Makefile's built-in `CFLAGS = -g -Wall`. -j1: make's jobserver
            # mkfifo is not permitted on HMDFS; -lm is required by the math
            # functions (sin/cos/atan2/...) used for media rotation.
            autotools = Autotools(self)
            autotools.make(target="poster", args=["-e", "-j1"])

    def package(self):
        # Upstream `make install` hardcodes `strip poster` plus absolute
        # /usr/local/{bin,man} destinations; stage the package tree manually.
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "poster", src, bindir)
        copy(self, "poster.1", src, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "README", src, os.path.join(self.package_folder, "share", "doc", "poster"))
        copy(self, "COPYING", src, os.path.join(self.package_folder, "share", "doc", "poster"))
        copy(self, "manual.ps", src, os.path.join(self.package_folder, "share", "doc", "poster"))

    def package_info(self):
        # CLI application: only bindirs, no libraries.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
