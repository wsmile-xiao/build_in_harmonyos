#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Libdshconfig, libdshconfig, 0.20.13, libdshconfig 0.20.13, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibdshconfigConan(ConanFile):
    name = "libdshconfig"
    version = "0.20.13"
    description = "A library to read dsh config file style data files"
    license = "GPL-2.0-or-later"
    homepage = "https://www.netfort.gr.jp/~dancer/software/"
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
        # R26: Static linking (BUILD_SHARED_LIBS=OFF equivalent for autotools)
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Update config.guess/config.sub for HarmonyOS platform recognition
        automake_share = os.path.join(os.path.dirname(shutil.which("automake")), "..", "share")
        for d in sorted(os.listdir(automake_share), reverse=True):
            if d.startswith("automake-"):
                cg = os.path.join(automake_share, d, "config.guess")
                cs = os.path.join(automake_share, d, "config.sub")
                if os.path.isfile(cg) and os.path.isfile(cs):
                    shutil.copy(cg, os.path.join(self.source_folder, "config.guess"))
                    shutil.copy(cs, os.path.join(self.source_folder, "config.sub"))
                    break
        # Fix HMDFS umask issue: autoconf uses umask 077 for temp dirs which
        # fails on HMDFS filesystem (cannot write files in 700-perm dirs)
        configure_script = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_script):
            with open(configure_script, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_script, "w") as f:
                f.write(content)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["dshconfig"]
