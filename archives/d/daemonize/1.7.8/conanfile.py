#!/usr/bin/env python3
"""Conan recipe — daemonize 1.7.8

Command-line utility to run a program as a Unix daemon.
Originally written by Marshall Ellis (bmc).

Build system: autotools (pre-generated configure + Makefile.in).
Produces a single binary `daemonize` installed to sbin/.

OHOS specifics:
  - HMDFS setgid causes `umask 077 && mktemp -d` to create directories with
    `drwx--S---` (2700) permissions, blocking owner writes. Patch changes
    `umask 077` to `umask 022` in the configure script.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DaemonizeConan(ConanFile):
    name = "daemonize"
    version = "1.7.8"
    description = "Run a command as a Unix daemon"
    license = "BSD-3-Clause"
    homepage = "https://github.com/bmc/daemonize"
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

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["sbin"]
