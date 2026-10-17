#!/usr/bin/env python3
"""Conan recipe for micron — GNU cron daemon and client.

Autotools project producing the `micrond` daemon (sbin) and the `crontab`
client (bin), modeled on the units/2.22 and bc/1.07.1 precedents.

Device notes:
- The OHOS Conan profile exports SHELL/CONFIG_SHELL pointing at
  /data/service/hnp/bin/bash, whose getcwd() currently fails in build
  directories; autoconf re-executes itself through $CONFIG_SHELL, so
  configure aborts with "working directory cannot be determined". All build
  commands are therefore prefixed with `env -u CONFIG_SHELL SHELL=/bin/sh`.
- OHOS musl has no POSIX thread-cancellation API (knowledge base E085); the
  patches under patches/ replace micron's pthread_cancel-based thread
  shutdown with a cooperative scheme (stop flag + wakeups + join).
- `make` descends into doc/, which regenerates the manual with makeinfo
  (absent on OHOS); the shipped doc artifacts are touched first so they are
  used as-is.
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
    " --build=aarch64-unknown-linux-gnu"
    " --host=aarch64-unknown-linux-gnu"
)
# Documentation artifacts shipped with the tarball; refreshing their mtimes
# keeps makeinfo/help2man out of the build (never touch Makefile.am/in — that
# would trigger an automake regeneration instead).
DOC_SUFFIXES = (".info", ".info-1", ".info-2", ".info-3", ".info-4", ".info-5",
                ".1", ".5", ".8")


class MicronConan(ConanFile):
    name = "micron"
    version = "1.4"
    description = "GNU micron — a minimal cron implementation (daemon and client)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org.ua/software/micron/"
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
        # Upstream (2024) config.sub does not know the linux-ohos triplet.
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ])
        tc.generate()

    def _touch_doc(self):
        """Refresh the mtimes of the documentation artifacts shipped in the
        tarball so makeinfo/help2man are never invoked."""
        doc = os.path.join(self.source_folder, "doc")
        if not os.path.isdir(doc):
            return
        for name in os.listdir(doc):
            if name.endswith(DOC_SUFFIXES):
                os.utime(os.path.join(doc, name), None)

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # HMDFS: mktemp temp dir under umask 077 becomes unwritable for
        # config.status (knowledge E011/E114) — relax to 002.
        replace_in_file(self, os.path.join(src, "configure"),
                        "umask 077", "umask 002")

        self._touch_doc()

        self.run(f'cd "{src}" && {SH} sh configure {CONFIGURE_ARGS}')
        self.run(f'cd "{src}" && {SH} make -j1')

    def package(self):
        src = self.source_folder
        # `make` rewrites doc/version.texi & co., which makes the manual look
        # stale again for `make install` — refresh once more.
        self._touch_doc()
        self.run(f'cd "{src}" && {SH} make install DESTDIR="{self.package_folder}/"')

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
