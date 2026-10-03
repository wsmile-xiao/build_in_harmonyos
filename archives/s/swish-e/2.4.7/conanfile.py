#!/usr/bin/env python3
"""Conan recipe for swish-e 2.4.7 (OHOS PC aarch64 adaptation).

SWISH-E is the Simple Web Indexing System for Humans - Enhanced: a
veteran (2009-era) flat-file web/embedded-systems indexer built on
autotools.  Upstream tarball ships a pre-generated configure script,
builds a single CLI executable (src/swish-e) plus libswish-e, and its
only external build dependency is zlib (bundled fallback exists but we
link the OHOS SDK zlib).

Two OHOS-specific adaptations (see knowledge/drafts entries):

  1. Legacy config.guess (2009) does not recognize the OHOS/aarch64
     triplet -> configure fails with "cannot guess build type".
     Mitigation without a config.guess patch: pass an explicit
     --build=aarch64-unknown-linux-gnu triplet (autotools accepts a
     build triple it does not know as long as it is well-formed).
     The same mitigation also satisfies --host via --build.
  2. Upstream defines its own internal helper ``uncompress2()`` in
     src/compress.{c,h} (a varint decoder, nothing to do with zlib's
     zlib-uncompress API added in zlib 1.2.3.5+).  Modern zlib headers
     (OHOS SDK) declare ``uncompress2`` as a function taking
     (Bytef*, uLongf*, const Bytef*, uLongf*) -> int, which conflicts
     with the internal declaration at translate time.  Mitigation:
     rename the internal symbol to ``swish_uncompress2`` (patch 0001).

Design notes:
  R26: delivers a CLI executable + its private libswish-e; no system
       library has the swish-e basename.
  R32: platform guard accepts Linux and OHOS.
  R33: no raw shell env vars; compiler injected via configure CC.
  R34: test_package executes the built swish-e binary end-to-end
       (index -> search) — see test_package/.
  R39: conandata.yml points at the official upstream tarball
       (Debian pool mirror of swish-e_2.4.7.orig.tar.gz).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class SwishEConan(ConanFile):
    name = "swish-e"
    version = "2.4.7"
    description = (
        "SWISH-E — Simple Web Indexing System for Humans - Enhanced: "
        "flat-file full-text indexer for web and embedded collections"
    )
    license = "GPL-2.0-or-later"
    homepage = "http://swish-e.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def configure(self):
        # The OHOS profile declares settings.os.version=6.0, but the build
        # and package_id do not depend on it (same pattern as other OHOS
        # recipes in this repository).
        self.settings.rm_safe("os.version")

    def export_sources(self):
        # Ship the OHOS patches with the recipe so build() can apply them
        # (conandata has no patches section; applying is done in build()).
        src = os.path.join(self.recipe_folder, "patches")
        if os.path.isdir(src):
            copy(self, "*", src, os.path.join(self.export_folder, "patches"))

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "swish-e is only supported on Linux/OHOS, not "
                f"{self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Patch 0001 equivalent: rename the internal uncompress2 ->
        # swish_uncompress2 (zlib.h symbol clash, see module docstring).
        # Applied textually in source() so the fix is independent of patch
        # tooling; patches/0001-*.patch documents the same change as a
        # reviewable diff.
        src_dir = os.path.join(self.source_folder, "src")
        for fn in os.listdir(src_dir):
            if not fn.endswith((".c", ".h")):
                continue
            path = os.path.join(src_dir, fn)
            with open(path, "r", errors="replace") as fh:
                text = fh.read()
            if "uncompress2" in text:
                with open(path, "w") as fh:
                    fh.write(text.replace("uncompress2",
                                          "swish_uncompress2"))

    def build(self):
        # (The uncompress2 rename is applied in source(); see the note
        # there and patches/0001-*.patch for the reviewable diff.)

        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration("upstream configure missing")

        # --build with an explicit, well-formed triplet: the 2009-era
        # config.guess cannot detect OHOS/aarch64 and configure aborts with
        # "cannot guess build type".  See knowledge/drafts/README.md.
        #
        # CFLAGS="-O1": the 2009 codebase misbehaves at -O2 on 64-bit
        # (SIGSEGV in remove_worddata_longs during "Writing word data" —
        # pointer/long type-punning in the worddata writer).  -O0 and -O1
        # are both verified clean end-to-end (index + search); -O1 keeps
        # reasonable performance without the optimizer bug.
        build_triplet = "aarch64-unknown-linux-gnu"
        cc = os.environ.get("CC", "clang")
        cmd = (
            f'./configure --disable-shared --disable-nls '
            f'--build={build_triplet} --host={build_triplet} '
            f'CC="{cc}" CFLAGS="-Wall -fPIC -O1" '
            f'--prefix={self.package_folder}'
        )

        # E011 (knowledge/graph/E011.kv): configure creates its config.status
        # scratch dir with `umask 077 && mktemp -d -q ./confstatXXXXXX`.  On
        # HMDFS the UID mapping (dir owner 20001006 vs process UID) makes
        # the resulting 0700/setgid dir unwritable for the current process,
        # so config.status fails on every step ("./confstatCdCeEK/out:
        # Permission denied", CI build #66719) and the Makefile never gets
        # generated.  A relaxed *process* umask does not help (mktemp's dir
        # mode is enforced by the FS, not the caller).  Root fix: neutralise
        # the umask inside configure itself before it runs — same approach
        # as archives/m/mbr/1.2.2.
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            with open(configure, "r", errors="replace") as fh:
                text = fh.read()
            patched = text.replace("(umask 077 && mktemp",
                                   "(umask 022 && mktemp")
            patched = patched.replace("(umask 077 && mkdir",
                                      "(umask 022 && mkdir")
            if patched != text:
                with open(configure, "w") as fh:
                    fh.write(patched)
                os.chmod(configure, 0o755)
                self.output.info(
                    "E011: relaxed configure's umask 077 -> 022 for the "
                    "config.status scratch dir (HMDFS UID mapping)")

        self.run(cmd, cwd=self.source_folder)

        # E074/R9: parallel make trips the HMDFS jobserver fifo on workers
        # (CI #66701: "make: jobserver mkfifo: Operation not permitted").
        # Use -j1 and drop any inherited MAKEFLAGS jobserver reference.
        self.run("MAKEFLAGS= make -j1",
                 cwd=os.path.join(self.source_folder, "src"))

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        copy(self, "swish-e", os.path.join(src, "src"),
             os.path.join(pkg, "bin"))
        copy(self, "libswish-e.so*", os.path.join(src, "src", ".libs"),
             os.path.join(pkg, "lib"))
        copy(self, "COPYING", src, os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
