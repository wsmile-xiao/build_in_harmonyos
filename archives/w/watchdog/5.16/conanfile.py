#!/usr/bin/env python3
"""Conan recipe — watchdog 5.16

Linux watchdog daemon — monitors system health and reboots if unresponsive.
Originally written by Michael Meskes and Paul Crawford.

Build system: autotools (pre-generated configure + Makefile.in).
Produces three binaries installed to bin/:
  - watchdog: the main watchdog daemon
  - wd_keepalive: keepalive helper for when watchdog is stopped
  - wd_identify: identify the watchdog device

OHOS specifics:
  - HMDFS FUSE filesystem remaps file ownership, causing config.status's
    umask 077 to create inaccessible temp directories. Patch changes
    umask 077 to umask 0 in the configure script.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WatchdogConan(ConanFile):
    name = "watchdog"
    version = "5.16"
    description = "Linux watchdog daemon — monitors system health and reboots if unresponsive"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/watchdog/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

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
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
