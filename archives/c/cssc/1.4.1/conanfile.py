#!/usr/bin/env python3
"""Conan recipe — cssc 1.4.1 (GNU CSSC, an SCCS-compatible source code
version control system).

Autotools project; the patches in conandata.yml carry the OHOS
(HarmonyOS PC) adaptations:

1. build-aux/config.guess + config.sub: recognise HarmonyOS
   (aarch64-unknown-linux-ohos triplet) — the 2016-era scripts do not
   know this OS.
2. src/file.cc + src/sccs.c: on environments whose UIDs have no
   /etc/passwd entry (OHOS app sandboxes), getpwuid() returns NULL;
   fall back to $USER / "unknown" instead of aborting (unconditional
   POSIX logic, no platform ifdef — R8).
3. src/bodyio.cc + src/sccs.c: tmpfile() uses P_tmpdir (/tmp) which
   may be read-only (OHOS); fall back to an unlinked mkstemp file in
   $TMPDIR, closing the descriptor if fdopen() fails.
4. src/sccsdiff.sh.in: use ${TMPDIR:-/tmp} for scratch files and try the
   script's own directory when locating the companion "get" tool.
5. testutils/decompress_stdin.sh.in: GNU gzip cannot decompress legacy
   compress(1) .Z (LZW) fixtures and no ncompress is available on OHOS;
   decompress via python3 (gzip first, then a standard-library-only
   LZW fallback — no external dependencies).
6. tests + bundled googletest 1.6: honour ${TMPDIR:-/tmp} instead of the
   hardcoded read-only /tmp (not-root, delsfile, gtest CapturedStream,
   test_linebuf tmpfile helper); replace obsolescent `egrep` (GNU grep
   3.12 prints a deprecation warning on stderr which breaks strict
   stderr comparisons).

The recipe additionally relaxes `umask 077` to `umask 022` in the
generated `configure` at build time (E011): on HMDFS-backed conan
caches, config.status' `mktemp -d` scratch directory cannot be written
otherwise ("could not setup config files machinery").
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class CsscConan(ConanFile):
    name = "cssc"
    version = "1.4.1"
    description = "GNU CSSC - a compatibly structured source code version control system (SCCS-compatible)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/cssc/"
    url = "https://ftp.gnu.org/gnu/cssc/CSSC-1.4.1.tar.gz"
    topics = ("sccs", "version-control", "cssc")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Static build: the SCCS tools are self-contained command line
        # utilities; no shared library is exported.
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E011: on HMDFS-backed conan caches the `umask 077` that
        # configure/config.status applies before `mktemp -d
        # "./confXXXXXX"` produces a 0700(+setgid) directory that the
        # build process cannot write into ("could not setup config
        # files machinery").  Relaxing the umask for these two
        # scratch-directory creations keeps the generated tree world
        # readable and fixes the failure (same fix as numdiff E011).
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        # The sccs front-end lives in bin/; the individual SCCS tools
        # (admin, get, delta, prs, ...) are installed into libexec/cssc/.
        self.cpp_info.resdirs = []
