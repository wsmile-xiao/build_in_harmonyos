#!/usr/bin/env python3
"""Conan recipe for GNU Autoconf Archive — a collection of reusable M4 macros."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AutoconfArchiveConan(ConanFile):
    name = "autoconf-archive"
    version = "2024.10.16"
    description = "GNU Autoconf Archive — a collection of reusable M4 macros for autotools projects"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/autoconf-archive/"
    url = ""

    package_type = "build-scripts"

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
        # Create a dummy makeinfo to bypass doc build on OHOS (texinfo not available)
        makeinfo_bindir = os.path.join(self.build_folder, ".makeinfo-bin")
        os.makedirs(makeinfo_bindir, exist_ok=True)
        makeinfo_path = os.path.join(makeinfo_bindir, "makeinfo")
        with open(makeinfo_path, "w") as f:
            f.write("#!/bin/sh\n"
                    "while [ $# -gt 0 ]; do\n"
                    '  case "$1" in\n'
                    '    -o) shift; touch "$1"; exit 0 ;;\n'
                    "    *) shift ;;\n"
                    "  esac\n"
                    "done\n"
                    "exit 0\n")
        os.chmod(makeinfo_path, 0o755)
        os.environ["PATH"] = f"{makeinfo_bindir}:{os.environ.get('PATH', '')}"

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]
        aclocal_path = os.path.join(self.package_folder, "share", "aclocal")
        self.buildenv_info.define_path("ACLOCAL_PATH", aclocal_path)
