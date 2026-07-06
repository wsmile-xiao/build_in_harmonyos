#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Gnuwhich, gnu-which, 2.25, gnu-which 2.25, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnuwhichConan(ConanFile):
    name = "gnu-which"
    version = "2.25"
    description = "GNU which utility - find full path of shell commands"
    license = "GPL-3.0-or-later"
    homepage = "https://savannah.gnu.org/projects/which/"
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
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # Pass CC/CXX/SHELL as configure args to override conan profile env vars
        # that may point to non-existent paths (e.g. /data/service/hnp/bin/...)
        configure_args = []
        if self.settings.os in ("Linux", "OHOS"):
            bash_path = shutil.which("bash") or "/bin/sh"
            cc_path = shutil.which("clang") or "clang"
            cxx_path = shutil.which("clang++") or "clang++"
            configure_args = [
                f'CC={cc_path}',
                f'CXX={cxx_path}',
                f'SHELL={bash_path}',
            ]
        autotools.configure(args=configure_args)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # gnu-which is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
