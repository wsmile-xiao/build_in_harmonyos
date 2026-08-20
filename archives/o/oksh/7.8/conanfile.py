#!/usr/bin/env python3
"""Conan recipe — oksh 7.8 (Autotools)"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OkshConan(ConanFile):
    name = "oksh"
    version = "7.8"
    description = "Portable OpenBSD ksh shell"
    license = "ISC"
    homepage = "https://github.com/ibara/oksh"

    package_type = "application"

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
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        # oksh.1 man page is in source dir, not build dir
        src_man = "oksh.1"
        if os.path.isfile(os.path.join(self.source_folder, src_man)):
            copy(self, src_man, self.source_folder, self.build_folder)
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
