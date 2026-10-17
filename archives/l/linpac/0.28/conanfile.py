#!/usr/bin/env python3
"""Conan recipe — LinPac 0.28 for HarmonyOS PC (aarch64-linux-ohos).

LinPac ("Linux Packet Radio") is a curses-based AX.25 packet-radio terminal.
``libexec/linpac/linpac`` is the terminal itself, the programs installed next to
it (``mail``, ``getmsg``, ``telnet``, ``w``, ``mheard``, ``logbook``, ...) are
the packet-radio applications that talk to it over the LinPac application
protocol, and ``liblinpac``/``libaxmail`` are the plugin API libraries those
applications are linked against.

Dependency: ncurses/6.6 (wide-character build, published on ohpcd).

OHOS adaptations (see notes.md and patches/):
  * build-aux/config.guess / config.sub: teach the ``aarch64-unknown-linux-ohos``
    triplet so the 2009-era scripts stop rejecting the OHOS host.
  * configure: link the wide-character curses library (``-lncursesw``) instead
    of ``-lncurses``/``-ltermcap``; the Conan package ships a static
    ``libncursesw.a`` and nothing else.
  * configure: ``umask 077`` -> ``022`` for the config.status temporary
    directory (E114: HMDFS forces setgid and a 077 directory is not writable).
  * configure: the AX.25 ``listen`` companion program does not exist on OHOS;
    the hard configure error becomes a warning and the ``listen`` window simply
    stays unavailable.
  * src/compat/linux/ax25.h: wrapper for the truncated OHOS ``<linux/ax25.h>``
    (``sockaddr_storage`` clash with ``<sys/socket.h>`` + missing
    ``SIOCPROTOPRIVATE``), placed ahead of the sysroot include path.
  * mail_screen.cc / linpac.cc: the Conan ncurses is built with the opaque API
    (``NCURSES_OPAQUE``), so WINDOW internals are expressed with the public
    ``getmaxx()``/``getmaxy()``/``clearok()`` calls.
  * linpac.cc: OHOS has no ``/var/lock``; the per-user lock file falls back to a
    writable runtime directory (``$LINPAC_LOCKDIR`` > ``$XDG_RUNTIME_DIR`` >
    ``$TMPDIR``).
  * linpac.cc still uses the ``register`` storage class, removed in the C++17
    dialect of the OHOS profile; handled with ``-Wno-error=register`` (E293).
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LinpacConan(ConanFile):
    name = "linpac"
    version = "0.28"
    description = ("LinPac — AX.25 packet radio terminal (curses client, LinPac "
                   "application protocol helpers and plugin API libraries)")
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/linpac/"
    url = "https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/tree/main/archives/l/linpac/0.28"

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Only the wide-character static libncursesw.a is shipped by the package.
        self.requires("ncurses/6.6")

    def validate(self):
        # R32: settings.os must be checked with in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"linpac is only adapted for Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsDeps: feed -I/-L/-l of ncurses into configure/make
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # OHOS: calls.h / data.cc / sources.cc include <linux/ax25.h>, whose
        # sysroot copy is unusable.  src/compat ships a wrapper that has to be
        # found before the sysroot include path (-I beats -isystem).
        compat = os.path.join(self.source_folder, "src", "compat")
        tc.extra_cflags.append(f"-I{compat}")
        tc.extra_cxxflags.append(f"-I{compat}")
        # E293: this 1998-era code still uses the `register` storage class
        # (linpac.cc) which is removed in the C++17 dialect forced by the OHOS
        # profile; keep it as a warning instead of touching the source.
        tc.extra_cxxflags.append("-Wno-error=register")
        # Application: keep the bundled plugin libraries static so that no
        # libtool RUNPATH into the Conan package folder is baked into the
        # executables (OHOS does not resolve $ORIGIN reliably).
        tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()

    def build(self):
        # HMDFS extraction may drop the executable bit of the Autotools
        # helpers; `configure` is executed directly.
        for rel in ("configure", "build-aux/config.guess", "build-aux/config.sub",
                    "build-aux/install-sh", "build-aux/missing",
                    "build-aux/depcomp", "build-aux/compile"):
            path = os.path.join(self.source_folder, rel)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])  # R9/E074: HMDFS jobserver fifo is not usable

        # Upstream ships no automated test suite; `make check` is the documented
        # entry point and is a no-op.  Run it anyway and keep the evidence.
        self.run("make -k check > upstream-make-check.log 2>&1",
                 cwd=self.build_folder, ignore_errors=True)

    def package(self):
        Autotools(self).install()

    def package_info(self):
        # Standalone terminal + helper programs; the plugin API archives are
        # internal and therefore not exposed to consumers.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin", "libexec/linpac"]
