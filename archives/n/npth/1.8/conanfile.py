#!/usr/bin/env python3
"""Conan recipe for npth 1.8 — GNU Portable Threads library.

Build system: autotools (configure + make).
License: LGPL-2.1-or-later
Homepage: https://gnupg.org/software/npth/

Platform adaptations:
  - config.guess/config.sub: HarmonyOS detection (patches 0001, 0002)
  - configure: pthread_cancel→pthread_create for musl compat (patch 0003)
  - configure: use TMPDIR for config.status temp dir (patch 0003)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NpthConan(ConanFile):
    name = "npth"
    version = "1.8"
    description = "GNU Portable Threads library — lightweight threading based on pthread"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnupg.org/software/npth/"
    # URL is set by CI from conandata.yml, no need to set here

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
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
        self.cpp_info.libs = ["npth"]
