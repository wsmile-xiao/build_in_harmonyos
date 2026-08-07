#!/usr/bin/env python3
"""Conan recipe — macchanger 1.7.0-r3 (GNU MAC Changer).

A utility for manipulating the MAC address of network interfaces.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MacchangerConan(ConanFile):
    name = "macchanger"
    version = "1.7.0-r3"
    description = "GNU MAC Changer - utility for manipulating the MAC address of network interfaces"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/alobbs/macchanger"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # GitHub tag archive lacks configure script; need automake for autoreconf
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Source from GitHub tag archive lacks a configure script
        autotools = Autotools(self)
        autotools.autoreconf(args=["--install", "--force"])
        # E129: Fix HMDFS umask issue in generated configure
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_path, "w") as f:
                f.write(content)
        autotools.configure()
        # MAKEINFO=true: skip texinfo doc build (not needed for the binary)
        autotools.make(args=["-j1", "MAKEINFO=true"])

    def package(self):
        autotools = Autotools(self)
        # Use MAKEINFO=true to avoid texinfo dependency during install
        autotools.install(args=["MAKEINFO=true"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
