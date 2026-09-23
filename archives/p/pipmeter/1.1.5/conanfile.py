#!/usr/bin/env python3
"""Conan recipe -- pipmeter 1.1.5 (Autotools).

pipemeter is a single-file C CLI utility that shows the speed of data
moving from stdin to stdout, with an optional progress bar.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PipmeterConan(ConanFile):
    name = "pipmeter"
    version = "1.1.5"
    description = "CLI utility that shows the speed of data moving from input to output"
    license = "GPL-2.0-or-later"
    homepage = "https://launchpad.net/pipemeter"

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
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # In-source build: upstream Makefile.in has no VPATH support
        # ("pipemeter: pipemeter.c" requires the sources in the build dir),
        # so configure and make must run inside the source tree.
        with chdir(self, self.source_folder):
            # E011: autoconf 2.59 configure uses "umask 077 && mktemp -d",
            # which fails on HMDFS (same fix as pv/1.7.24). configure is a
            # generated file, so it is fixed at build time, not via patches/.
            self.run("sed -i 's/umask 077/umask 022/g' configure")
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
        # No upstream automated tests exist: Makefile.in defines no "check"
        # target and testscript.sh is a manual 200M benchmark that mails
        # results to the author (see test_package/MANIFEST.yml audit), so
        # no "make check" step runs here by design.

    def package(self):
        # Upstream "make install" relies on GNU "install -Dp -t", which is
        # unavailable in minimal OHOS environments, so install the two
        # deliverables (binary + man page) directly instead.
        copy(self, "pipemeter", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "pipemeter.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
