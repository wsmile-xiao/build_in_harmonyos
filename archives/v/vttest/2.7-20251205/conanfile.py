#!/usr/bin/env python3
"""Conan recipe for vttest 2.7 (snapshot 20251205) — VT100/ANSI terminal test program.

vttest is Thomas E. Dickey's maintained version of Per Lindberg's 1985 program
that verifies a VT100-compatible terminal (or emulator).  The operator runs it
*on* the terminal under test and picks menu items that drive cursor movement,
character sets, colors, keyboard/mouse reports, VT52/VT220/VT320/VT420/VT520
and xterm extensions.  The package ships the ``vttest`` executable and its
manpage; there are no libraries or headers.

Upstream identifies this snapshot as 2.7 with patch date 20251205
(patchlev.h: RELEASE 2 / PATCHLEVEL 7 / PATCH_DATE 20251205); the tarball is
published as ``vttest-20251205.tgz``.

OHOS adaptation notes:

* ``configure`` (autoconf output) creates its temporary work directory with
  ``umask 077``; HMDFS force-sets the setgid bit, so the directory ends up
  ``drwx--S---`` and rejects writes even from its owner, and ``config.status``
  aborts with "could not setup config files machinery".
  ``patches/0002-configure.patch`` rewrites both ``umask 077`` uses to
  ``umask 022`` (knowledge base E129/E112/E136; same accepted fix as
  a52dec/0.7.4 and teseq/1.1.1).
* ``config.guess`` (timestamp 2025-07-10) does not recognise the HarmonyOS
  kernel reported by uname, so ``configure`` stops with "cannot guess build
  type; you must specify one" (the same script also builds its compiler-probe
  directory with ``umask 077``).  ``patches/0001-config.guess.patch`` adds the
  ``aarch64:HarmonyOS`` mapping to ``aarch64-unknown-linux-$LIBC`` and relaxes
  those umasks, so the native build identifies itself and configure proceeds
  without ``--host``; the config.sub shipped upstream already understands
  ``linux-ohos`` should a host triplet ever be passed explicitly.
* Upstream has no automated test suite: vttest *is* the terminal test tool and
  its checks need an operator at the terminal by design (see
  test_package/MANIFEST.yml for the R51 inventory).  ``build()`` therefore runs
  no ``make check`` (the makefile has no such target); regression assertions
  live in ``test_package/`` and are executed by ``conan create``, including a
  PTY-driven smoke test that starts the packaged binary on a real
  pseudo-terminal.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class VttestConan(ConanFile):
    name = "vttest"
    version = "2.7-20251205"
    description = ("VT100/ANSI terminal test program: menu-driven escape-sequence, "
                   "character-set, color and keyboard/mouse conformance tests")
    license = "MIT"
    homepage = "https://invisible-island.net/vttest/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("terminal", "vt100", "ansi", "escape-sequences", "testing")

    # Command-line tool (bin/vttest plus share/man/man1/vttest.1), no libraries.
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "vttest targets POSIX terminals (autoconf + POSIX tty API); "
                f"got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Command-line tool: expose the binary; consumers reach it through the
        # Conan runtime environment.  No headers or libraries are shipped.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "vttest")
        self.cpp_info.set_property("cmake_target_name", "vttest::vttest")
        self.cpp_info.set_property("pkg_config_name", "vttest")
