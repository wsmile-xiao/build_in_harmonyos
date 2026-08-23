#!/usr/bin/env python3
"""Conan recipe for smartmontools 7.4 — S.M.A.R.T. monitoring utilities.

smartmontools is a command-line tool (smartctl, smartd) for monitoring
storage devices using S.M.A.R.T. It uses autotools build system.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SmartmontoolsConan(ConanFile):
    name = "smartmontools"
    version = "7.4"
    description = "Utilities for monitoring storage devices using S.M.A.R.T."
    license = "GPL-2.0"
    homepage = "https://www.smartmontools.org/"

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
        # Fix umask in configure for HMDFS setgid directory compatibility.
        # On HMDFS, directories inherit setgid from parent, and umask 077
        # creates temp dirs without group execute, causing Permission denied.
        replace_in_file(self, os.path.join(self.source_folder, "configure"), "umask 077", "umask 027")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
