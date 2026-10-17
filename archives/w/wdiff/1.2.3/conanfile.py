#!/usr/bin/env python3
"""Conan recipe — wdiff 1.2.3

GNU wdiff: word-level diff front-end to GNU diff. Installs the `wdiff`
command-line utility (experimental programs mdiff/unify stay off by default).
Upstream 1.2.3 ships an Autotools build with bundled gnulib, so there are
no external library dependencies.

Build system: Autotools (release tarball ships configure).
License: GPL-3.0-or-later.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
import os

from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WdiffConan(ConanFile):
    name = "wdiff"
    version = "1.2.3"
    description = "GNU wdiff — word-level diff between files (front-end to GNU diff)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/wdiff/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # NOTE: wdiff is a front-end and exec()s GNU `diff` at runtime
        # (DIFF_PROGRAM). diffutils is NOT bundled as a conan dependency
        # because it is not yet published on the registry; consumers are
        # expected to provide GNU diff on PATH (same as upstream's design).
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # AM_GNU_GETTEXT(external): OHOS/musl has no libintl, disable NLS
        tc.configure_args.append("--disable-nls")
        # Upstream config.guess (2014) cannot guess the build type on OHOS;
        # cross triplets must be given explicitly (E-knowledge: build=gnu, host=ohos)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # makeinfo is absent on OHOS, so the info page must never be rebuilt.
        # automake's stamp-vti chain refreshes doc/version.texi on every run,
        # which would stale the prebuilt wdiff.info; pin those timestamps in
        # dependency order (newest last) so make considers everything current
        doc_src = os.path.join(self.source_folder, "doc")
        for f in ("wdiff.texi", "stamp-vti", "version.texi"):
            os.utime(os.path.join(doc_src, f), None)
        copy(self, "wdiff.info", doc_src,
             os.path.join(self.build_folder, "doc"))
        # conan's copy() preserves the source mtime; stamp the copy newest so
        # make sees it as up to date against version.texi
        os.utime(os.path.join(self.build_folder, "doc", "wdiff.info"), None)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
