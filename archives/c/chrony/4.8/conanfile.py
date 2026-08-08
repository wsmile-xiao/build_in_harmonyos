#!/usr/bin/env python3
"""Conan recipe for chrony 4.8 on OHOS."""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ChronyConan(ConanFile):
    name = "chrony"
    version = "4.8"
    description = "Versatile implementation of the Network Time Protocol"
    license = "GPL-2.0-only"
    homepage = "https://chrony-project.org/"
    url = "https://chrony-project.org/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # chrony's hand-written configure script only supports in-tree builds.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"chrony does not support {self.settings.os}")

        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # HarmonyOS has Linux-compatible time/socket APIs, but chrony's
            # platform detector only recognises the upstream system names.
            tc.configure_args.append("--host-system=Linux")
            # These facilities depend on Linux-specific devices or privileged
            # services which are not exposed to HarmonyOS PC applications.
            tc.configure_args.extend([
                "--disable-rtc",
                "--disable-phc",
                "--disable-pps",
                "--disable-privdrop",
                "--disable-timestamping",
            ])
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
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
