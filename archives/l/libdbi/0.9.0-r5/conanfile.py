#!/usr/bin/env python3
"""Conan recipe for the libdbi 0.9.0-r5 HarmonyOS adaptation."""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibdbiConan(ConanFile):
    name = "libdbi"
    version = "0.9.0-r5"
    description = "Database-independent abstraction layer for C"
    license = "LGPL-2.1-or-later"
    homepage = "https://libdbi.sourceforge.net/"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="libdbi-0.9.0.tar.gz",
            strip_root=True,
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-docs",
                "--without-ltdl",
                "--enable-shared" if self.options.shared else "--disable-shared",
                "--disable-static" if self.options.shared else "--enable-static",
            ]
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["dbi"]
        self.cpp_info.set_property("cmake_file_name", "libdbi")
        self.cpp_info.set_property("cmake_target_name", "libdbi::libdbi")
        self.cpp_info.set_property("pkg_config_name", "dbi")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl"]
