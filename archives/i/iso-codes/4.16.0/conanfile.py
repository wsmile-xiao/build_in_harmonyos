#!/usr/bin/env python3
"""Conan recipe for iso-codes 4.16.0.

iso-codes is a data-only package providing ISO standard codes
(country, language, script, currency) as JSON data files with
gettext translations. No C/C++ library is produced.

HMDFS platform note: autotools configure uses umask 077 for temp
directory creation, which causes Permission denied on HMDFS. A patch
(0001-configure-umask-hmdfs.patch) changes this to umask 022 and
uses TMPDIR for temp directory path.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IsoCodesConan(ConanFile):
    name = "iso-codes"
    version = "4.16.0"
    description = "ISO country, language, script and currency codes and translations"
    license = "LGPL-2.1-or-later"
    homepage = "https://salsa.debian.org/iso-codes-team/iso-codes"
    url = ""

    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.resdirs = ["share"]
