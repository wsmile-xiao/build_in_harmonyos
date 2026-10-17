#!/usr/bin/env python3
"""Conan recipe — liburcu (Userspace RCU) 0.15.7 (Autotools)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LiburcuConan(ConanFile):
    name = "liburcu"
    version = "0.15.7"
    description = "Userspace RCU (read-copy-update) library for synchronized data structures"
    license = "LGPL-2.1-or-later"
    homepage = "https://lttng.org/urcu/"
    url = ""  # CI fills this

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
        # R26: system-name libraries default to static (avoid .so pollution of /lib /lib64)
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
        self.cpp_info.libs = [
            "urcu",
            "urcu-bp",
            "urcu-cds",
            "urcu-common",
            "urcu-mb",
            "urcu-memb",
            "urcu-qsbr",
        ]
