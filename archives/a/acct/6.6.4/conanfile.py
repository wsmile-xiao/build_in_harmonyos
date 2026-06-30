#!/usr/bin/env python3
"""Conan recipe for GNU Accounting Utilities (acct) 6.6.4.

acct is a CLI tool package - it produces executables, not libraries.
R26 (static linking for system same-name libs) does not apply since
acct has no shared libraries.

Platform notes (OHOS):
- config.guess/config.sub modified to recognize HarmonyOS as Linux-compatible
- configure script umask 077 -> 022 to fix HMDFS temp directory permission issue
- accton uses acct() syscall which is not implemented on OHOS (E051)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AcctConan(ConanFile):
    name = "acct"
    version = "6.6.4"
    description = "GNU Accounting Utilities - process and login accounting tools"
    license = "GPL-3.0"
    homepage = "https://www.gnu.org/software/acct/"
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
        # acct produces only executables, no system same-name libraries
        # R26 does not apply - no -static needed
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # acct is a CLI tool package - no libraries to link against
        # Binaries are exposed via bindirs
        self.cpp_info.libs = []
