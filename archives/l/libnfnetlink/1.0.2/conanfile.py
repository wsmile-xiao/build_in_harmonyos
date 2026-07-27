#!/usr/bin/env python3
"""Conan recipe — libnfnetlink 1.0.2 (Autotools)"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibnfnetlinkConan(ConanFile):
    name = "libnfnetlink"
    version = "1.0.2"
    description = "Low-level library for netfilter related communication"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.netfilter.org/projects/libnfnetlink/"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System same-name library — disable shared to avoid polluting /lib, /lib64
        tc.configure_args.append("--disable-shared")
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS fix: umask 077 creates 700-permission temp dirs that HMDFS cannot write to
        replace_in_file(self, os.path.join(self.source_folder, "configure"), "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["nfnetlink"]
