#!/usr/bin/env python3
"""Conan recipe — pipemeter 1.1.5 (autoconf, single-file CLI tool).

pipemeter reports throughput / ETA of data flowing through a pipe:
    tar cf - dir | pipemeter | nc host 9999

Build system: plain autoconf `configure` + a hand-written Makefile.in
(no automake, no config.guess/config.sub, no AC_CANONICAL_HOST).

OHOS notes (see notes.md for the full trail):
- configure aborts with "could not setup config files machinery": HMDFS
  ignores umask/chmod, so `mktemp -d` yields drwx--S--- dirs that the
  owner cannot write into (knowledge E114).  Patch 0002 replaces the
  mktemp bootstrap with a plain `mkdir -p`.
- `install` is not available on OHOS (/bin is off PATH and toybox install
  has no -D/-t support), while the tarball already ships autoconf's
  portable install-sh.  Patch 0001 rewires the Makefile install rule to it.
- Upstream probes for pow in -lm and stores the result in POW_LIB, but the
  Makefile never references @POW_LIB@; with musl the link still resolves
  pow() through the clang builtin, so no extra -lm is injected here.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PipemeterConan(ConanFile):
    name = "pipemeter"
    version = "1.1.5"
    description = (
        "Command-line tool that reports throughput, block size and ETA of "
        "data moving through a stdin/stdout pipe"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://launchpad.net/pipemeter"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream needs nothing beyond libc/libm (configure only probes
        # getopt.h/getopt_long and pow, all satisfied by the OHOS musl
        # sysroot), so there is no Conan dependency to declare.
        pass

    def layout(self):
        basic_layout(self)
        # Upstream ships a hand-written Makefile.in with no VPATH/srcdir
        # support (`pipemeter: pipemeter.c`), so configure/make must run in
        # the source folder. Out-of-tree builds die with
        # "No rule to make target 'pipemeter.c'" (same shape as
        # bandwidthd/2.0.1-cvs20090917 and audtty/0.1.12).
        self.folders.build = self.folders.source

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R1: only the prefix matters; AutotoolsToolchain injects it and the
        # compiler/flag environment. No --enable-static/--disable-shared:
        # upstream configure accepts neither.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
