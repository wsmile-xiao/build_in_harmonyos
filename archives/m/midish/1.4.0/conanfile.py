#!/usr/bin/env python3
"""Conan recipe for midish 1.4.0 on HarmonyOS PC (aarch64-linux-ohos).

midish is a MIDI sequencer/filter implemented as a small command interpreter.
The package ships the `midish` binary, the `smfplay` and `smfrec` shell
front-ends, their man pages, the documentation and the example song/rc files.

The project comes with its own hand written `configure` script and
`Makefile.in` (no autotools), and builds in-source, so the recipe runs
configure/make/make install directly from the source folder. The MIDI backend
is chosen by configure from `uname`: on HarmonyOS neither the ALSA nor the
sndio branch is active, so the portable "raw" backend is compiled in (the
command interpreter and the upstream regression suite do not need a MIDI
device).

OHOS-specific adaptation (patches/):
  - 0001: the non-tty stdin poll path only accepted POLLIN. A pipe that
    reaches end-of-file may report only POLLHUP, so the interpreter never saw
    end-of-file and kept polling without ever exiting (every batch script and
    the whole upstream regression suite hung). POLLHUP is now treated as
    readable, which makes read() return 0 and terminates the interpreter.
  - 0002: the GitHub tag archive used as source does not ship version.h (it is
    generated when the release tarball is packed), so configure would write its
    placeholder string ("midish (unknown release)"). The release version.h is
    restored so that `midish -b` + `version` keeps reporting "midish 1.4.0".

Upstream tests: `make check` runs the regress/ suite (143 command/result
cases) against the freshly built interpreter and is executed from build().
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MidishConan(ConanFile):
    name = "midish"
    version = "1.4.0"
    description = "MIDI sequencer/filter with its own command interpreter (midish, smfplay, smfrec)"
    license = "ISC"
    homepage = "https://midish.org"
    url = "https://midish.org"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # The upstream build is in-source (configure writes Makefile next to
        # the sources).
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_settings(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = compilers.get("c", "clang")
        cflags = "-O2 -fPIC"
        ldflags = ""
        return cc, cflags, ldflags

    def build(self):
        apply_conandata_patches(self)

        cc, cflags, ldflags = self._compiler_settings()
        configure = [
            "./configure",
            "--prefix=/",
            "--datadir=/share",
            "--mandir=/share/man",
            "CC={}".format(cc),
            'CFLAGS="{}"'.format(cflags),
        ]
        if ldflags:
            configure.append('LDFLAGS="{}"'.format(ldflags))
        jobs = self.conf.get("tools.build:jobs", default=None)
        self.run(" ".join(configure))
        self.run("make -j{}".format(jobs) if jobs else "make")
        if self.settings.os == "OHOS":
            # Upstream regression suite: 143 command/result cases executed
            # against the freshly built interpreter (regress/run-test).
            self.run("make check")

    def package(self):
        self.run('make install DESTDIR="{}"'.format(self.package_folder))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
