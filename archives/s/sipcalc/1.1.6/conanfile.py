#!/usr/bin/env python3
"""Conan recipe for sipcalc 1.1.6 — IP subnet calculator (autotools, C).

sipcalc is a CLI tool that performs IPv4/IPv6 subnet calculations.
Build with autotools (configure + make + make install).

HMDFS adaptation:
  configure patch uses TMPDIR instead of ./confXXXXXX (umask 077 issue).

R32: OHOS uses settings.os in ("Linux", "OHOS").
R28: test_package/ exists.
R34: test_package executes the actual sipcalc binary.
R38: sipcalc is a CLI tool -> commands.json declared at software level.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SipcalcConan(ConanFile):
    name = "sipcalc"
    version = "1.1.6"
    description = "Advanced console-based IP subnet calculator"
    license = "BSD-3-Clause"
    homepage = "https://github.com/sii/sipcalc"
    url = ""  # CI fills this

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
        # OHOS preflight workaround: pwd/getcwd fails in some conan build dirs
        # because parent path chain is broken.  Set PWD env var explicitly
        # and chdir to the build folder so the shell's pwd has a fallback.
        import os
        bf = self.build_folder
        if os.path.isdir(bf):
            os.chdir(bf)
            os.environ["PWD"] = bf
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []