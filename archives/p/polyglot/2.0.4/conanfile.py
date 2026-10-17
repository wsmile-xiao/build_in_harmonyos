#!/usr/bin/env python3
"""Conan recipe — polyglot 2.0.4 (Autotools).

PolyGlot is a UCI-to-XBoard adapter and opening-book tool by Fabien Letouzey.
It builds a single command-line binary (no library), so package_type is
"application" and package_info only exposes bindirs.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PolyglotConan(ConanFile):
    name = "polyglot"
    version = "2.0.4"
    description = "PolyGlot — UCI to XBoard protocol adapter and chess opening-book tool (make-book/merge-book/dump-book)"
    license = "GPL-2.0"
    homepage = "https://www.gnu.org/software/xboard/"
    url = "https://ftp.debian.org/debian/pool/main/p/polyglot/"

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
        src = self.source_folder
        with chdir(self, src):
            # E490: restore executable modes of autotools helper scripts
            # (may be lost when the source tarball is unpacked from the conan cache)
            self.run("chmod +x configure config.guess config.sub install-sh missing 2>/dev/null || true")
            # E129: HMDFS always sets setgid on new directories; umask 077 in the
            # shipped configure creates drwx--S--- temp dirs that block config.status
            self.run("sed -i 's/umask 077/umask 022/g' configure")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
