#!/usr/bin/env python3
"""Conan recipe — simstring 1.0 (SimString approximate string matching).

SimString is a header-only C++ library (include/simstring/*.h) shipped with
a command-line frontend (`simstring`) that builds/retrieves n-gram databases.
There is no libtool in upstream 1.0, so nothing produces a .a/.so: the only
compiled artifact is the CLI binary installed to bin/.

Build system: autotools (bundled configure from autoconf 2.6x, 2010).

OHOS/HarmonyOS adaptation (see patches/ and notes.md):
  * 0001 config.guess: 2009 baseline does not know `uname -s = HarmonyOS`;
    add a HarmonyOS branch emitting aarch64-unknown-linux-ohos (same
    semantics as scripts/patch-autotools-ohos.pl, knowledge E007).
  * 0002 config.sub: same baseline lacks aarch64 and linux-ohos.
  * 0003 configure: HMDFS drops the group-write bit for `umask 077` temp
    dirs (owner is mapped to a shared id) -> `config.status` cannot create
    ./confXXXXXX/subs1.awk; relax to `umask 022` (a52dec precedent).
  * 0004 simstring.h: `#include <unistd.h>` for read/write/lseek declarations
    (Debian patch 0001 "To use standard library correctly").
  * source(): the upstream server labels .tar.gz responses with
    `Content-Encoding: gzip`/`x-gzip` in every observed form (4 header
    shapes tested), so Conan's requests/urllib3 stack transparently decodes
    one layer and hashes the inner plain tar (1187840 B,
    sha256 fa0fa2969ec5be85e5752156c469ffef07fb90f4780e77d2a57beb1ccf34cdb0)
    instead of the canonical .tar.gz file bytes (233446 B,
    sha256 386f5e18c9a92a84eccd6caee407e28da939dd74bb68bd17912c4d918f0e4171
    == official dist == Debian .dsc Checksums-Sha256 == plain `curl -O`).
    conandata keeps the canonical file-face sha (W0 three-way same-source
    anchoring; W4 reviewers recompute it with curl), and source() falls back
    to urllib — which does no Content-Encoding decoding, so the raw file
    bytes land and check_sha256 pins 386f5e18. Same pattern as blepvco
    0.1.0; the "declare the decoded hash instead" variant was used by
    bsdgames-nonfree 2.17 only because its double-gzip response could not
    be fetched raw (declared both faces in a conandata comment).

No --build/--host is passed: knowledge E007 forbids it (it flips configure
into cross_compiling mode and skips AC_RUN_IFELSE probes).
"""
import os
import urllib.request
from urllib.parse import urlparse

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (get, apply_conandata_patches,
                               export_conandata_patches, check_sha256, unzip)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SimstringConan(ConanFile):
    name = "simstring"
    version = "1.0"
    description = "SimString - simple and efficient approximate string matching library with CLI frontend"
    license = "BSD-3-Clause"
    homepage = "https://www.chokkan.org/software/simstring/index.html.en"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Header-only library + CLI frontend; upstream builds no .a/.so, so no
    # `shared` option exists (plain autoconf, no libtool).
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No hard dependencies: configure only probes libc headers, libm and
        # mmap (all part of the OHOS sysroot); upstream ships no third-party
        # code. Evidence: configure.in AC_CHECK_* list + Debian Build-Depends
        # (debhelper-compat only).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        data = self.conan_data["sources"]
        try:
            get(self, **data, strip_root=True)
            return
        except ConanException as exc:
            # chokkan.org serves .tar.gz with `Content-Encoding: gzip`/`x-gzip`
            # on every response shape we tested; Conan's requests/urllib3
            # decodes one layer, so the sha256 check sees the inner plain tar
            # (fa0fa296...) and fails against the canonical file-face hash
            # (386f5e18..., == official dist == Debian .dsc, curl -O repro).
            # urllib does NOT decode Content-Encoding: the raw .tar.gz bytes
            # land, check_sha256 pins the canonical hash, then unzip.
            # (blepvco 0.1.0 precedent; bsdgames-nonfree 2.17 declared the
            # decoded face instead — impossible here, this file is single-gzip.)
            self.output.warning(
                "conan downloader failed ({}); retrying with urllib "
                "(server responds Content-Encoding: x-gzip on .tar.gz)".format(exc)
            )
        filename = os.path.basename(urlparse(data["url"]).path) or "simstring-1.0.tar.gz"
        archive = os.path.join(self.source_folder, filename)
        with urllib.request.urlopen(data["url"], timeout=120) as resp:
            payload = resp.read()
        with open(archive, "wb") as handler:
            handler.write(payload)
        check_sha256(self, archive, data["sha256"])
        unzip(self, archive, destination=self.source_folder, strip_root=True)
        os.remove(archive)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E007: never pass --build/--host here — config.guess/config.sub are
        # patched instead (0001/0002) so the triplet stays a native build.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Upstream is tiny (~20 TUs); serial build keeps the log deterministic.
        autotools.make(args=["-j1"])

    def package(self):
        # Installs bin/simstring, include/simstring/*.h and share/doc/simstring.
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Header-only: nothing to link, but the package ships the CLI binary.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
