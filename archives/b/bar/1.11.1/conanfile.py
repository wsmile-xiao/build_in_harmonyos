#!/usr/bin/env python3
"""Conan recipe for bar — the Command Line Progress Bar (clpbar).

bar processes a stream of data and prints a display on stderr showing the
amount of data passed, throughput, and (when the total size is known) the
estimated time remaining and a progress bar.

Build system: autotools. No third-party dependencies (libc only).
R15: no --build/--host override; platform runtime probes (AC_TRY_RUN) are
exercised for real during configure.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BarConan(ConanFile):
    name = "bar"
    version = "1.11.1"
    description = "Command Line Progress Bar — show information about a data transfer"
    license = "GPL-2.0-or-later"
    homepage = "http://clpbar.sourceforge.net/"
    url = ""
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"bar is supported only on Linux/OHOS, got {self.settings.os}"
            )

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
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream test suite: make check runs test-types, test-001, test-002
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
