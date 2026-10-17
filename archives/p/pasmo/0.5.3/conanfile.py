#!/usr/bin/env python3
"""Conan recipe for pasmo 0.5.3 — portable Z80 cross-assembler.

pasmo is a Z80 cross-assembler written in standard C++ (9 translation units,
no third-party dependencies).  It emits raw binary, Intel HEX, CP/M Plus PRL,
Spectrum +3DOS/TAP/TZX/CDT (tape images for Spectrum and Amstrad CPC
emulators), Amstrad CPC Amsdos and MSX BLOAD images; starting with 0.5.0 it
can also translate Z80 sources into 8086 code for MS-DOS .COM and CP/M-86
.CMD files.

Adaptation notes (HarmonyOS PC, aarch64):
  * W0: no third-party dependencies — C++ standard library and libc only
    (`requirements()` intentionally absent).
  * The upstream release tarball ships a pre-generated Autotools tree
    (configure from GNU Autoconf 2.60, Makefile.in, aclocal.m4,
    install-sh/missing/depcomp) and the recipe runs the real upstream
    configure + make + install.  configure.ac declares only AC_PROG_CXX
    (no AC_CANONICAL_HOST), so there is no config.guess/config.sub
    canonicalization to port; the compiler comes from the Conan toolchain
    (R33), never from a bare shell variable.
  * pasmo.speccy.org closes connections from Python's default User-Agent
    (RemoteDisconnected) while accepting curl/wget-style clients, so
    source() downloads the official tarball with a curl User-Agent header;
    URL and sha256 are unchanged.
  * patches/0001-configure.patch: config.status creates its temporary
    directory with umask 077; on HMDFS an 0700 directory is not writable by
    the build process (knowledge E011), so configure aborts Makefile
    generation with "Permission denied".  The patch creates the directory
    with umask 022 instead.  No platform macro (R8/PF5), no system-prefix
    injection (PF6).
  * Upstream tests: 0.5.3 ships no test suite — no tests/ tree, Makefile.am
    declares only `bin_PROGRAMS = pasmo` (no TESTS/check_PROGRAMS/
    check-local) and the automake `check` target executes zero cases
    ("Nothing to be done for 'check'").  build() still runs `make check` so
    every build log carries that evidence; test_package/test_pasmo.sh
    provides the consumer-side regression tests required for the
    no-upstream-tests case (R51; evidence in test_package/MANIFEST.yml).

Artifacts: bin/pasmo (software-level commands.json declares the CLI, R38).
License: GPL-2.0-or-later (upstream COPYING shipped in licenses/).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class PasmoConan(ConanFile):
    name = "pasmo"
    version = "0.5.3"
    description = (
        "Portable Z80 cross-assembler emitting raw binary, Intel HEX, CP/M "
        "PRL, Spectrum TAP/TZX/CDT/+3DOS, Amstrad CPC Amsdos and MSX images "
        "(plus 8086 code for .COM/.CMD files)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://pasmo.speccy.org/"
    url = "https://pasmo.speccy.org/"
    topics = ("assembler", "z80", "8086", "retro-computing", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: check the OHOS family, not `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pasmo requires a POSIX host (Linux or OHOS), not {0}".format(
                    self.settings.os
                )
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # pasmo.speccy.org (an old nginx host) closes connections from
        # Python's default User-Agent (RemoteDisconnected), while curl/wget
        # style clients are accepted; present a curl UA so the official
        # source stays downloadable from the recipe.  URL and sha256 are
        # unchanged (R39), the tarball content is byte-identical.
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            headers={"User-Agent": "curl/8.8.0"},
        )
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — the HMDFS jobserver FIFO breaks parallel make (E074).
        autotools.make(args=["-j1"])
        # Upstream 0.5.3 ships no tests; keep the automake check target in the
        # build log as the zero-case evidence declared in MANIFEST.yml (R51).
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
