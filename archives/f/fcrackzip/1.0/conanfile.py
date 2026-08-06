#!/usr/bin/env python3
"""Conan recipe — fcrackzip 1.0 (Autotools).

ZIP archive password cracker supporting brute-force and dictionary attacks.
Source fixes applied via replace_in_file() in build() due to form feed
character incompatibility with Conan's patch parser.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FcrackzipConan(ConanFile):
    name = "fcrackzip"
    version = "1.0"
    description = "ZIP archive password cracker supporting brute-force and dictionary attacks"
    license = "GPL-2.0"
    homepage = "https://github.com/hyc/fcrackzip"
    url = ""

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

        # Fix 1: crack.h - add config.h include guard
        crack_h = os.path.join(self.source_folder, "crack.h")
        replace_in_file(self, crack_h, "#define CRACK_H\n", '#define CRACK_H\n\n#ifdef HAVE_CONFIG_H\n#include "config.h"\n#endif\n')

        # Fix 2: getopt.c - change <config.h> to "config.h"
        getopt_c = os.path.join(self.source_folder, "getopt.c")
        replace_in_file(self, getopt_c, '#include <config.h>', '#include "config.h"')

        # Fix 3: getopt1.c - change <config.h> to "config.h"
        getopt1_c = os.path.join(self.source_folder, "getopt1.c")
        replace_in_file(self, getopt1_c, '#include <config.h>', '#include "config.h"')

        # Fix 4: configure - umask 077 creates temp dirs with setgid but no
        # group execute (drwx--S---) on OHOS, preventing file creation.
        conf = os.path.join(self.source_folder, "configure")
        replace_in_file(self, conf, "umask 077", "umask 022")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
