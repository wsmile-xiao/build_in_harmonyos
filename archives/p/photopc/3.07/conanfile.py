#!/usr/bin/env python3
"""Conan recipe for photopc 3.07 (HarmonyOS PC adaptation).

Builds the photopc/epinfo command line tools (serial digital camera
control + EPSON photo file info extractor).  Upstream ships no test suite;
behavior is verified by the test_package consumer running the packaged
binaries with assertions.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PhotopcConan(ConanFile):
    name = "photopc"
    version = "3.07"
    description = "photopc/epinfo: command line tools for Epson/Agfa/Olympus serial digital cameras"
    license = "MIT"
    homepage = "http://photopc.sourceforge.net/"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("photopc supports Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # The bundled configure (autoconf 2.13 era) has no config.guess;
            # it checks the platform via uname and works natively on the
            # device, so no --build/--host bypass is needed (E007 forbid_1).
            pass
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Drop man pages/compressed duplicates: keep the package to
        # bin/ + docs needed at runtime (man pages are not runtime assets).
        mandir = os.path.join(self.package_folder, "share", "man")
        if os.path.isdir(mandir):
            import shutil

            shutil.rmtree(mandir, ignore_errors=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
