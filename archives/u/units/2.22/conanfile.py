#!/usr/bin/env python3
"""Conan recipe for units — GNU unit conversion program.

Autotools project producing the `units` CLI (application package).
Hand-written based on the bc/1.07.1 archived precedent.
"""
import os
from conan import ConanFile
from conan.tools.files import get, replace_in_file, apply_conandata_patches, export_conandata_patches, copy, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UnitsConan(ConanFile):
    name = "units"
    version = "2.22"
    description = "GNU units — converts between different systems of measurement units"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/units/"
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
        # units 2.22 (2021) config.sub does not know the linux-ohos triplet;
        # treat as a native aarch64 build (vo-aacenc/0.1.3 precedent).
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # HMDFS: mktemp temp dir under umask 077 becomes unwritable for
        # config.status (knowledge E011/E114) — relax to 002.
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 002")

        # install-info would regenerate units.info via makeinfo, which is not
        # available on OHOS/CI — keep install-man only (bc/1.07.1 precedent).
        replace_in_file(self, os.path.join(self.source_folder, "Makefile.in"),
                        "install-doc: install-man install-info",
                        "install-doc: install-man")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # install-support installs currency.units into $sharedstatedir/units
        # ($prefix/com) and leaves a DESTDIR-absolute symlink behind in
        # share/units, which breaks once the package folder moves. Flatten:
        # drop the symlink, copy the real file into share/units, drop com/.
        share_units = os.path.join(self.package_folder, "share", "units")
        com_units = os.path.join(self.package_folder, "com", "units")
        if os.path.isdir(com_units):
            sym = os.path.join(share_units, "currency.units")
            if os.path.islink(sym):
                rm(self, "currency.units", share_units)
                copy(self, "currency.units", com_units, share_units, keep_path=False)
            rmdir(self, os.path.join(self.package_folder, "com"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
