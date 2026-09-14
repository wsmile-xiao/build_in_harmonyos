#!/usr/bin/env python3
"""Conan recipe — coolmail 1.3

Coolmail is an X11 mail notification utility: it watches a mailbox file and
animates a small 3D envelope in a window (an xbiff replacement that can also
launch a mail reader when clicked).

Build system: hand-written GNU Makefile, no configure script, no upstream
test suite.  The Makefile hard-codes `-I/usr/X11R5/include` and
`-L/usr/X11R6/lib`, so the recipe passes the real Conan dependency
directories on the make command line instead of patching the Makefile.

The optional digitized-audio backend (upstream `AUDIO`/`-DAUDIO`, an OSS
/dev/mixer + /dev/dsp implementation behind `#ifdef linux`) cannot be built
or used on OHOS, so this recipe builds the sound-less configuration that the
upstream README documents ("comment these out if you can't ... use the
digitized audio feature").  See notes.md for the full deviation list.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rename,
)
from conan.tools.layout import basic_layout


class CoolmailConan(ConanFile):
    name = "coolmail"
    version = "1.3"
    description = ("X11 mail notification utility — watches a mailbox file and "
                   "animates a 3D envelope in a window (xbiff replacement)")
    license = "GPL-1.0-or-later"
    homepage = "https://sources.debian.org/src/coolmail/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The window is driven through the X Toolkit Intrinsics
        # (XtInitialize / XtCreateManagedWidget / XtAddEventHandler in
        # system/X11/display_list.c).  libxt propagates libx11, libsm,
        # libice and xorgproto for headers and linking.
        self.requires("libxt/1.3.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"coolmail supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # X11 dependency paths
    # ------------------------------------------------------------------
    def _dependency_dirs(self, kind):
        """Absolute include/lib directories of every host dependency."""
        attr = "includedirs" if kind == "include" else "libdirs"
        found, seen = [], set()
        for _, dep in self.dependencies.host.items():
            base = dep.package_folder or ""
            for entry in getattr(dep.cpp_info, attr):
                path = entry if os.path.isabs(entry) else os.path.join(base, entry)
                if os.path.isdir(path) and path not in seen:
                    seen.add(path)
                    found.append(path)
        return found

    def generate(self):
        self._x_include_dirs = self._dependency_dirs("include")
        self._x_lib_dirs = self._dependency_dirs("lib")

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from the Conan conf / profile, never from the
        # shell environment.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        cflags = "-O2" if self.settings.build_type == "Release" else "-O0 -g"

        includes = " ".join(f"-I{d}" for d in self._x_include_dirs)
        libdirs = " ".join(f"-L{d}" for d in self._x_lib_dirs)
        # The upstream Makefile lists `-lXext`, but no source file calls an
        # Xext entry point (checked with nm on the built objects) and no
        # libXext matching the libx11/1.8.13 graph is published for OHOS,
        # so the unused flag is dropped here.
        libs = f"{libdirs} -lXt -lX11 -lm"

        # R9: -j1 for this six-file 1995 Makefile.
        # AUDIO/AUDIO_MODULE are emptied on the command line: the audio
        # backend compiles only with -DAUDIO and is OSS/Linux specific.
        self.run(
            f'make -j1 CC="{cc}" CFLAGS="{cflags}" INCLUDES="{includes}" '
            f'LIB_DIRS="{libdirs}" LIBS="{libs}" AUDIO= AUDIO_MODULE=',
            cwd=self.source_folder,
        )

    def package(self):
        # The upstream `make install` target silently skips the copy when
        # BINDIR/MANDIR are not writable (HMDFS permission handling), so the
        # install rules are reproduced here with explicit file copies.
        copy(self, "coolmail", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "coolmail.man", src=self.source_folder, dst=man_dir)
        rename(self, os.path.join(man_dir, "coolmail.man"),
               os.path.join(man_dir, "coolmail.1"))

        x11_dir = os.path.join(self.package_folder, "share", "X11", "app-defaults")
        copy(self, "Coolmail.ad", src=self.source_folder, dst=x11_dir)
        rename(self, os.path.join(x11_dir, "Coolmail.ad"),
               os.path.join(x11_dir, "Coolmail"))

    def package_info(self):
        # Command-line application: no headers and no libraries.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
