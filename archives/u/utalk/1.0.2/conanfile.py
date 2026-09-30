#!/usr/bin/env python3
"""Conan recipe for utalk 1.0.2 — UDP-based full-screen "talk" client.

Upstream : https://utalk.ourproject.org/  (Roger Espel Llima / E. Bosch)
Language : ANSI C
Build    : hand-written POSIX Makefile (no autotools / cmake / meson)
Artifact : a single executable `utalk` -> CLI tool (R38 -> commands.json)

Dependency (only third-party): ncurses/6.6.  utalk calls the external termcap
API (tgetent/tgetstr/tgetnum/tgoto/tputs, declared in its own termcap.h); on
OHOS those symbols come from the published ncurses recipe.

OHOS notes:
  * ncurses is a system-same-name library -> linked STATICALLY (R26) so the
    published libncursesw.a cannot hijack /lib/libncursesw.so at runtime.
  * Linking ncurses statically also exposes ncurses' own `beep` symbol, which
    collides with utalk's termcap.c `beep()`.  Resolved with
    -Wl,--allow-multiple-definition (repo precedent: cflow / dovecot / ettercap);
    the object-file definition wins, which is the upstream intent.
  * The Makefile's own CFLAGS is deliberately NOT overridden: its OPT5 passes
    -DLIBDIR="..." which menu.c's HELPFILE macro needs.  Passing CFLAGS on the
    make command line drops OPTS and breaks the build.
  * Upstream `make install` runs `strip` and `chown root:root`; package() does a
    plain staged copy instead (portable, root-less).
  * The ncurses screen needs a terminfo database at runtime and OHOS ships almost
    none, so the ncurses terminfo DB is bundled into the package and exported via
    the TERMINFO run environment variable (device-verified on OHOS).
"""
import glob
import io
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class UtalkConan(ConanFile):
    name = "utalk"
    version = "1.0.2"
    description = ("UDP-based (SRDP) full-screen one-to-one talk client, an "
                   "alternative to the Unix talk program")
    license = "GPL-2.0-or-later"
    homepage = "https://utalk.ourproject.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Only third-party dependency; system-same-name lib -> static (R26).
        self.requires("ncurses/6.6")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"utalk supports Linux and OHOS, not {self.settings.os}")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                f"utalk/1.0.2 is validated for OHOS armv8, got {self.settings.arch}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: compiler comes from the Conan profile, never from shell vars.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = executables.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "profile must set tools.build:compiler_executables:c (R33)")
        return cc

    def _ncurses_libdir(self):
        ncurses = self.dependencies["ncurses"]
        libdir = ncurses.cpp_info.libdirs[0]
        if not os.path.isabs(libdir):
            libdir = os.path.join(ncurses.package_folder, libdir)
        return libdir

    def build(self):
        apply_conandata_patches(self)
        libdir = self._ncurses_libdir()
        # Command-line make variables override the Makefile assignments.
        # CFLAGS is intentionally left to the Makefile (see module docstring).
        make_vars = (
            "CC='%s' LIBS='-L%s -lncursesw' "
            "LDFLAGS='-Wl,--allow-multiple-definition'"
            % (self._cc(), libdir)
        )
        # Capture the build output through a pipe.  On some OHOS devices the
        # toolchain driver silently exits when its stdout/stderr is inherited
        # from the long python -> sh -> make -> sh chain; passing a StringIO
        # makes Conan use subprocess.PIPE (see conans conan_run), which is
        # stable.  The captured log is echoed back in full.
        buf = io.StringIO()
        self.run(f"make -j1 {make_vars} utalk",
                 cwd=self.source_folder, env="conanbuild",
                 stdout=buf, stderr=buf)
        self.output.info("---- utalk build log ----\n" + buf.getvalue())
        self.output.info(
            f"built utalk (CC={self._cc()}, LIBS=-L{libdir} -lncursesw, static ncurses)")

    def package(self):
        # Upstream `make install` strips the binary and chowns root:root — not
        # usable in a portable, root-less package step.  Staged copy instead.
        copy(self, "utalk", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "utalk.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # Bundle a terminfo database (utalk drives an ncurses screen, OHOS has
        # almost no system terminfo).  Same approach as the cbonsai recipe.
        ncurses = self.dependencies["ncurses"]
        for sub in ("share/terminfo", "lib/terminfo"):
            terminfo_dir = os.path.join(ncurses.package_folder, sub)
            if not os.path.isdir(terminfo_dir):
                continue
            destination = os.path.join(self.package_folder, "share", "terminfo")
            total = sum(
                os.path.getsize(os.path.join(root, name))
                for root, _, names in os.walk(terminfo_dir)
                for name in names
            )
            if total <= 8 * 1024 * 1024:
                copy(self, "*", src=terminfo_dir, dst=destination, keep_path=True)
            else:
                for entry in ("x", "xterm", "xterm-256color", "ansi",
                              "dumb", "linux", "vt100", "vt102"):
                    for f in glob.glob(os.path.join(terminfo_dir, entry)) + \
                            glob.glob(os.path.join(terminfo_dir, "?", entry + "*")):
                        copy(self, os.path.relpath(f, terminfo_dir),
                             src=terminfo_dir, dst=destination, keep_path=True)
            break

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        terminfo_dir = os.path.join(self.package_folder, "share", "terminfo")
        if os.path.isdir(terminfo_dir):
            self.runenv_info.append_path("TERMINFO", terminfo_dir)
