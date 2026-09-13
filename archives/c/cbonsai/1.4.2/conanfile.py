#!/usr/bin/env python3
"""Conan recipe for cbonsai 1.4.2.

A single-file C ncurses bonsai generator (GitLab jallbrit/cbonsai).  Plain
POSIX Makefile build — no autotools/cmake, so no automake requirement on
the OHOS device.

Every build knob is passed as a command-line make variable, which wholly
overrides the Makefile's own assignments (including its
`CFLAGS += $(shell pkg-config ...)` probe — pkg-config is not needed on
the device).  CC comes from the profile conf (R33), include/lib paths come
from the published ncurses dependency's cpp_info, and PREFIX=/ makes
`make install DESTDIR=<package_folder>` land bin/ and share/ directly in
the package root (packetq /usr/local-nesting lesson applied up front).
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CbonsaiConan(ConanFile):
    name = "cbonsai"
    version = "1.4.2"
    description = "ncurses bonsai tree generator, written in C"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.com/jallbrit/cbonsai"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Static libncursesw.a + libpanelw.a confirmed in the published
        # ohpcd payload (downloaded 2026-09-05).
        self.requires("ncurses/6.4")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cbonsai supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "profile must set tools.build:compiler_executables:c (R33)"
            )
        return cc

    def _ncurses_dirs(self):
        ncurses = self.dependencies["ncurses"]
        include = ncurses.cpp_info.includedirs[0]
        libdir = ncurses.cpp_info.libdirs[0]
        if not os.path.isabs(include):
            include = os.path.join(ncurses.package_folder, include)
        if not os.path.isabs(libdir):
            libdir = os.path.join(ncurses.package_folder, libdir)
        return include, libdir

    def build(self):
        apply_conandata_patches(self)
        include, libdir = self._ncurses_dirs()
        make_vars = (
            "CC='%s' PREFIX=/ "
            "CFLAGS='-I%s' "
            "LDLIBS='-L%s -lpanelw -lncursesw -lncursesw'"
            % (self._cc(), include, libdir)
        )
        # Command-line make variables suppress the Makefile's own
        # CFLAGS/LDLIBS assignments, so its `pkg-config` probes never run.
        self.run("make -j1 %s cbonsai" % make_vars, cwd=self.source_folder,
                 env="conanbuild")

    def package(self):
        include, libdir = self._ncurses_dirs()
        make_vars = (
            "CC='%s' PREFIX=/ DESTDIR='%s' "
            "CFLAGS='-I%s' "
            "LDLIBS='-L%s -lpanelw -lncursesw -lncursesw'"
            % (self._cc(), self.package_folder, include, libdir)
        )
        self.run("make -j1 %s install" % make_vars, cwd=self.source_folder,
                 env="conanbuild")
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # cbonsai (-p mode) goes through ncurses initscr(), which needs a
        # terminfo database.  The published ncurses package ships one but
        # its recipe never exposes it, and package_info-phase dependency
        # access yields package_folder=None (device-verified TypeError) —
        # so bundle the terminfo database INTO this package: the tool
        # becomes self-contained and the runtime hint below is a plain
        # static path.  Large databases are trimmed to common terminals.
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
                    for entry_file in glob.glob(os.path.join(terminfo_dir, entry)) + \
                            glob.glob(os.path.join(terminfo_dir, "?", entry + "*")):
                        relative = os.path.relpath(entry_file, terminfo_dir)
                        copy(self, relative, src=terminfo_dir, dst=destination,
                             keep_path=True)
            break

    def package_info(self):
        # Tool package (R38): commands.json at software level declares the
        # cbonsai command; no libraries, no consumer linkage.  TERMINFO
        # points at the terminfo database bundled by package() — a static
        # self.package_folder path, valid in every phase (no dependency
        # access here: transitive dependency package_folder is None during
        # package_info on this conan — device-verified TypeError).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        terminfo_dir = os.path.join(self.package_folder, "share", "terminfo")
        if os.path.isdir(terminfo_dir):
            self.runenv_info.append_path("TERMINFO", terminfo_dir)
