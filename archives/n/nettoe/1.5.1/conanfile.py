#!/usr/bin/env python3
"""Conan recipe — nettoe 1.5.1 (Autotools).

nettoe is a network tic-tac-toe game for the terminal.
Build system: autotools (configure + make).

This recipe enforces:
  R26: static linking for terminal tools (ncurses is static-only)
  R27: dependencies from @ohpcd/stable (none needed)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NettoeConan(ConanFile):
    name = "nettoe"
    version = "1.5.1"
    description = "Network tic-tac-toe game for the terminal"
    license = "GPL-2.0-or-later"
    homepage = "http://nettoe.sourceforge.net/"
    url = ""  # CI fills this

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
        # R26: Terminal tools must be statically linked.
        # ncurses is only available as a static library (libncurses.a),
        # so it is linked statically by default. The resulting binary
        # only depends on the system libc.so, satisfying R26.
        tc.generate()

    def build(self):
        # Patches include: config.guess/config.sub update (E007),
        # umask fix for HarmonyOS, duplicate symbol fix
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["nettoe"]
