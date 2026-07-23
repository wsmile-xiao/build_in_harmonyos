#!/usr/bin/env python3
"""Conan recipe for libnl 3.7.0 — Netlink Protocol Library Suite."""
import os

from conan import ConanFile
from conan.tools.files import export_conandata_patches, get, replace_in_file, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibnlConan(ConanFile):
    name = "libnl"
    version = "3.7.0"
    description = "Netlink Protocol Library Suite"
    license = "LGPL-2.1-only"
    homepage = "https://github.com/thom311/libnl"
    url = "https://github.com/thom311/libnl"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args = [
            "--build=aarch64-unknown-linux-gnu",
            "--prefix=/",
            "--disable-cli",
        ]
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # The release tarball includes configure. Do not autoreconf: this
        # environment lacks aclocal/automake. HMDFS requires readable temp files.
        replace_in_file(
            self, os.path.join(self.source_folder, "configure"), "umask 077", "umask 022"
        )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        core = self.cpp_info.components["nl-3"]
        core.set_property("pkg_config_name", "libnl-3.0")
        core.includedirs = ["include/libnl3"]
        core.libs = ["nl-3"]

        for component, pkg_config_name, library in [
            ("nl-route-3", "libnl-route-3.0", "nl-route-3"),
            ("nl-genl-3", "libnl-genl-3.0", "nl-genl-3"),
            ("nl-nf-3", "libnl-nf-3.0", "nl-nf-3"),
            ("nl-idiag-3", "libnl-idiag-3.0", "nl-idiag-3"),
            ("nl-xfrm-3", "libnl-xfrm-3.0", "nl-xfrm-3"),
        ]:
            info = self.cpp_info.components[component]
            info.set_property("pkg_config_name", pkg_config_name)
            info.libs = [library]
            info.requires = ["nl-3"]
