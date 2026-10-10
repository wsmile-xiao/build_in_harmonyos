#!/usr/bin/env python3
"""Conan recipe — qodem 1.0.1 (Autotools: configure + make).

qodem is a public-domain terminal emulator / BBS client (a from-scratch
Qmodem clone) built on the ncurses + termios + pty stack: it drives a child
shell through `forkpty()` and renders the result with wide-character
ncurses.

OHOS adaptation notes (details in notes.md and the patch descriptions):
  * 0001-configure-hmdfs-umask.patch — configure/config.status create their
    scratch directory with `umask 077`; HMDFS stores that directory with
    mode 0700 owned by the shared owner, so config.status cannot write into
    it and configure fails with "Permission denied" while creating
    `Makefile` (E678 umask-077 family).
  * 0002-qodem-getpwuid-null.patch — qodem_main() did
    `getpwuid(geteuid())->pw_name` with no NULL check.  Container uids
    (e.g. 20020085) have no /etc/passwd entry on OHOS, so every run except
    --help/--version died with SIGSEGV.
  * Upstream features that are unavailable on OHOS are switched off at
    configure time: gpm (libgpm is absent and configure aborts without
    --disable-gpm), sdl, upnp, x11 (PDCurses) and ssh (bundled cryptlib).
    Serial/modem support is deliberately kept: it compiles and exercises
    the termios ioctl path.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class QodemConan(ConanFile):
    name = "qodem"
    version = "1.0.1"
    package_type = "application"
    description = "Public-domain terminal emulator and BBS client (Qmodem clone)"
    license = "CC0-1.0"
    homepage = "https://qodem.sourceforge.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Wide-character ncurses (static); provides ncursesw symbols and the
        # TERMINFO / TERMINFO_DIRS run environment used at test time.
        self.requires("ncurses/6.6")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qodem supports Linux and OHOS only, got " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # AutotoolsToolchain does not inject dependency include/lib flags, so
        # put ncurses where configure's AC_CHECK_HEADERS/AC_CHECK_LIB can see
        # them (ncursesw/curses.h is not shipped, <curses.h> is; qodem falls
        # back to it in source/qcurses.h).
        ncurses = self.dependencies["ncurses"]
        tc.extra_cflags.append("-I" + os.path.join(ncurses.package_folder, "include"))
        tc.extra_ldflags.append("-L" + os.path.join(ncurses.package_folder, "lib"))
        tc.configure_args.extend(
            [
                "--disable-gpm",
                "--disable-sdl",
                "--disable-upnp",
                "--disable-x11",
                "--disable-ssh",
            ]
        )
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone terminal binary; no library is produced.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
