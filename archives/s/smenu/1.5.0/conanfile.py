#!/usr/bin/env python3
"""Conan recipe — smenu 1.5.0 (autotools).

smenu is a terminal CLI selection/filtering tool.
R26: static linking for terminal tools (ncurses linked statically).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SmenuConan(ConanFile):
    name = "smenu"
    version = "1.5.0"
    description = "smenu - terminal CLI selection and filtering tool"
    license = "MPL-2.0"
    homepage = "https://github.com/p-gen/smenu"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No external dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        # ncurses: only static libncursesw.a exists on this platform.
        # Add library path so configure can find ncurses, then force static link.
        tc.extra_cflags.append("-I/storage/Users/currentUser/usr/local/include")
        tc.extra_ldflags.append("-L/storage/Users/currentUser/usr/local/lib")
        tc.extra_ldflags.append("-l:libncursesw.a")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        src = self.source_folder
        # Fix config.guess/config.sub for HarmonyOS (aarch64-unknown-linux-ohos)
        # Copy system config.guess/config.sub from automake-1.17 (supports ohos)
        self.run(
            'cp -f /storage/Users/currentUser/usr/local/share/automake-1.17/config.guess '
            f'{src}/build-aux/config.guess')
        self.run(
            'cp -f /storage/Users/currentUser/usr/local/share/automake-1.17/config.sub '
            f'{src}/build-aux/config.sub')
        # Fix umask 077 -> 022 for HMDFS compatibility
        # Affects: configure, config.guess (and generated config.status)
        for fn in ["configure", "config.guess", "config.sub"]:
            fp = os.path.join(src, fn)
            if os.path.isfile(fp):
                self.run(f"sed -i 's/umask 077/umask 022/g' {fp}")
        autotools.configure()
        # Also fix generated config.status
        cs = os.path.join(src, "config.status")
        if os.path.isfile(cs):
            self.run(f"sed -i 's/umask 077/umask 022/g' {cs}")
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["smenu"]
