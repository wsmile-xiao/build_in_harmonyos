#!/usr/bin/env python3
"""Conan recipe — gnustep-make 2.9.2.1 (Autotools)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnustepMakeConan(ConanFile):
    name = "gnustep-make"
    version = "2.9.2.1"
    description = "GNUstep Make build system"
    license = "GPL-3.0-or-later"
    homepage = "https://gnustep.org/"
    url = "https://github.com/gnustep/tools-make"
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
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # gnustep-make installs executables and GNUstep Makefiles; it does not
        # provide a linkable library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.buildenv_info.append_path("PATH", self.package_folder + "/bin")
        self.runenv_info.append_path("PATH", self.package_folder + "/bin")
        self.runenv_info.define("GNUSTEP_MAKEFILES", self.package_folder + "/share/GNUstep/Makefiles")
