#!/usr/bin/env python3
"""Conan recipe — lcrq 0.3.1 (Librecast RaptorQ FEC library).

Upstream: https://git.sr.ht/~librecast/lcrq (RFC6330 RaptorQ FEC).
Autotools build; upstream src/Makefile only produces a shared library
(`all: $(SOFILE)`), no static target exists.

OHOS adaptations:
  - patches/0001+0002 (conandata.yml): teach the bundled config.guess /
    config.sub about HarmonyOS (E007).
  - build(): configure the in-source tree explicitly (`--srcdir=.`) and set
    the config.status temp-dir umask to 022 (E129/E114).  Both are applied
    inline instead of via patches/, because `configure` is a generated file
    shipped inside the release tarball (details in notes.md).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LcrqConan(ConanFile):
    name = "lcrq"
    version = "0.3.1"
    description = "LCRQ — C implementation of RFC6330 RaptorQ forward error correction (FEC) codes for Librecast"
    license = "GPL-2.0-or-later"
    homepage = "https://librecast.net/lcrq.html"
    url = "https://git.sr.ht/~librecast/lcrq"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass  # no third-party dependencies (pure C, libc only)

    def layout(self):
        # lcrq's hand-written Makefiles (Makefile.in) are in-source only:
        # `make -C src` expects the .c sources in the current tree (no VPATH),
        # so the build folder must be the source folder.
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # NOTE: upstream src/Makefile.in is hand-written and only builds the
        # shared object (all: $(SOFILE)); --enable-static/--disable-shared
        # are not honoured, so no static-linking args are passed here.
        # In-source build (see layout()): srcdir is "." by construction, so
        # state it explicitly.  configure otherwise has to fork `expr`/`sed`
        # to auto-detect srcdir and aborts with
        # "cannot find sources (src/) in  or .." whenever such a fork fails
        # (observed on CI workers under memory pressure).
        tc.configure_args.append("--srcdir=.")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._fix_hmdfs_tmpdir_umask()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _fix_hmdfs_tmpdir_umask(self):
        """E129/E114: config.status creates its temp dir with
        ``umask 077 && mktemp -d "./confXXXXXX"``.  On HMDFS that yields a
        drwx--S--- directory that cannot be written into, so config.status
        aborts with
            ./config.status: line NNN: ./confXXXXXX/subs1.awk: Permission denied
            config.status: error: could not setup config files machinery
        The failure is mount-dependent (not reproducible on every HMDFS), so
        create that temp dir with umask 022 instead -- the fix used by the
        other autotools archives here.
        Applied inline rather than as a patch: `configure` is a generated file
        shipped inside the release tarball, so the patches/ pipeline (which
        filters generated files) cannot carry it.
        """
        if self.settings.os != "OHOS":
            return
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure):
            self.output.warning(f"HMDFS umask fix: {configure} not found")
            return
        with open(configure, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        if "umask 077" not in text:
            self.output.warning(
                "HMDFS umask fix: 'umask 077' not found in configure (upstream "
                "text changed?); config.status may fail on setgid HMDFS mounts")
            return
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(text.replace("umask 077", "umask 022"))

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["lcrq"]
