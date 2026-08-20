#!/usr/bin/env python3
"""Conan recipe — gdbm (GNU DataBase Manager)

Autotools-based library: configure + make.
Provides libgdbm and libgdbm_compat (dbm/ndbm compatibility).
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GdbmConan(ConanFile):
    name = "gdbm"
    version = "1.23"
    description = "GNU database manager - lightweight key-value database library"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gdbm/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        tc.configure_args.append("--enable-libgdbm-compat")
        tc.configure_args.append("--disable-nls")
        tc.generate()

    def build(self):
        # Ensure TMPDIR is set for HarmonyOS (HMDFS does not support umask 077 temp dirs)
        os.environ.setdefault("TMPDIR", tempfile.gettempdir())
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1", "MAKEINFO=true"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["MAKEINFO=true"])

    def package_info(self):
        self.cpp_info.libs = ["gdbm_compat", "gdbm"]
        self.cpp_info.bindirs = ["bin"]
