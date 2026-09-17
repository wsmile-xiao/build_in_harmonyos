#!/usr/bin/env python3
"""Conan recipe for gnu-pw-mgr — GNU password manager.

Autotools project producing the `gnu-pw-mgr` and `sort-pw-cfg` CLI programs
(application package), modeled on the units/2.22 and bc/1.07.1 precedents.

Device notes:
- The OHOS Conan profile exports SHELL/CONFIG_SHELL pointing at
  /data/service/hnp/bin/bash, whose getcwd() currently fails in build
  directories; autoconf re-executes itself through $CONFIG_SHELL, so
  configure aborts with "working directory cannot be determined". All build
  commands are therefore prefixed with `env -u CONFIG_SHELL SHELL=/bin/sh`.
- OHOS musl provides <sys/time.h>; without `ac_cv_header_sys_time_h=yes`
  gnulib substitutes its own header and `struct timeval` is redefined.
- libintl/gettext are absent; `--disable-nls` keeps libopts on the pure macro
  fallback (clang 15 treats the implicit declarations as errors otherwise).
"""
import os
from conan import ConanFile
from conan.tools.files import get, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

SH = "env -u CONFIG_SHELL SHELL=/bin/sh"
CONFIGURE_ARGS = (
    "--prefix=/"
    " '--bindir=${prefix}/bin'"
    " '--sbindir=${prefix}/bin'"
    " '--libdir=${prefix}/lib'"
    " '--includedir=${prefix}/include'"
    " '--oldincludedir=${prefix}/include'"
    " ac_cv_header_sys_time_h=yes"
    " --disable-nls"
    " --build=aarch64-unknown-linux-gnu"
    " --host=aarch64-unknown-linux-gnu"
)


class GnuPwMgrConan(ConanFile):
    name = "gnu-pw-mgr"
    version = "2.7.4"
    description = "GNU gnu-pw-mgr — derives robust passwords from a single master password"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gnu-pw-mgr/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Upstream (2021) config.sub does not know the linux-ohos triplet.
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # HMDFS: mktemp temp dir under umask 077 becomes unwritable for
        # config.status (knowledge E011/E114) — relax to 002.
        replace_in_file(self, os.path.join(src, "configure"),
                        "umask 077", "umask 002")

        self.run(f'cd "{src}" && {SH} sh configure {CONFIGURE_ARGS}')
        self.run(f'cd "{src}" && {SH} make -j1')

    def package(self):
        src = self.source_folder

        # makeinfo is not available on OHOS; refresh the mtimes of the
        # documentation artifacts shipped in the tarball so that
        # `make install` copies them as-is instead of regenerating them.
        # Only generated artifacts are touched — refreshing Makefile.am/in
        # would trigger an automake regeneration instead.
        doc = os.path.join(src, "doc")
        if os.path.isdir(doc):
            for name in os.listdir(doc):
                if name.endswith((".info", ".info-1", ".info-2", ".info-3",
                                  ".info-4", ".info-5", ".8", ".5", ".1")):
                    os.utime(os.path.join(doc, name), None)

        self.run(f'cd "{src}" && {SH} make install DESTDIR="{self.package_folder}/"')

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
