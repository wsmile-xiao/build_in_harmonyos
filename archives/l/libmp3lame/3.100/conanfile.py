#!/usr/bin/env python3
"""Conan recipe — libmp3lame 3.100 (LAME MP3 encoder).

Build system: autotools (configure + make).
No external library dependencies.
"""
import os
import glob as _glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libmp3LameConan(ConanFile):
    name = "libmp3lame"
    version = "3.100"
    description = "LAME MP3 encoder library"
    license = "LGPL"
    homepage = "https://lame.sourceforge.io/"
    url = "https://gitee.com/opendesktop/ohpcd-recipes"  # CI overrides if needed

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix umask 077 → 022: setgid hmdfs makes umask 077 dirs unwritable
        _configure = os.path.join(self.source_folder, "configure")
        replace_in_file(self, _configure, "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool *.la wrappers
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["mp3lame"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs = ["include", "include/lame"]
        self.cpp_info.bindirs = ["bin"]
