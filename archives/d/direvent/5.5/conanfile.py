#!/usr/bin/env python3
"""Conan recipe for direvent — GNU directory event watcher daemon.

Autotools project producing the `direvent` CLI daemon (application package),
modeled on the units/2.22 and bc/1.07.1 precedents.

Device note (E386 family): the OHOS Conan profile exports SHELL/CONFIG_SHELL
pointing at /data/service/hnp/bin/bash. That bash currently fails getcwd()
when its working directory is a build directory ("shell-init: error
retrieving current directory"), and autoconf re-executes configure through
$CONFIG_SHELL, so configure aborts with "working directory cannot be
determined". configure/make/install are therefore invoked through
`env -u CONFIG_SHELL SHELL=/bin/sh`, which keeps the full Conan toolchain
environment but routes shell execution to the working /bin/sh.
"""
import os
from conan import ConanFile
from conan.tools.files import get, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

# Keep the Conan toolchain env, but do not let autoconf/make use the
# getcwd-broken hnp bash.
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


class DireventConan(ConanFile):
    name = "direvent"
    version = "5.5"
    description = "GNU direvent — monitors directory trees for filesystem events"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/direvent/"
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
        # GNU direvent 5.5 (2022) config.sub does not know the linux-ohos
        # triplet; treat as a native aarch64 build (units/vo-aacenc precedent).
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

        # Upstream test suite (tests/testsuite, 31 autotest cases) must run
        # for real inside build(): full `make check`, non-zero exit fails
        # the build (autotest summary exit code governs).
        # make check recurses into doc/, where MAKEINFO would try to
        # regenerate direvent.info with makeinfo (absent on OHOS).
        # Refresh the mtimes of the doc artifacts shipped in the tarball
        # so make considers them up to date (same approach as package()).
        doc = os.path.join(src, "doc")
        for name in ("direvent.info", "direvent.8", "direvent.conf.5"):
            path = os.path.join(doc, name)
            if os.path.isfile(path):
                os.utime(path, None)
        self.run(f'cd "{src}" && {SH} make -j1 check')

    def package(self):
        src = self.source_folder

        # makeinfo/help2man are not available on OHOS; refresh the mtimes of
        # the documentation artifacts shipped in the tarball so that
        # `make install` copies them as-is instead of regenerating them.
        # Only generated artifacts are touched — refreshing Makefile.am/in
        # would trigger an automake regeneration instead.
        doc = os.path.join(src, "doc")
        for name in ("direvent.info", "direvent.8", "direvent.conf.5"):
            path = os.path.join(doc, name)
            if os.path.isfile(path):
                os.utime(path, None)

        self.run(f'cd "{src}" && {SH} make install DESTDIR="{self.package_folder}/"')

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
