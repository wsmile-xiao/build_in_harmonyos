#!/usr/bin/env python3
"""Conan recipe for CppUnit 1.15.1 on HarmonyOS."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CppunitConan(ConanFile):
    name = "cppunit"
    version = "1.15.1"
    description = "C++ unit testing framework"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.documentfoundation.org/Development/Cppunit"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            ["--disable-shared", "--enable-static", "--disable-werror"]
        )
        if self.options.fPIC:
            tc.extra_cxxflags.append("-fPIC")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        if not cross_building(self):
            autotools.make(target="check", args=["-j1"])
        else:
            self.output.info("Cross-building: upstream runtime tests skipped")

    def package(self):
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["cppunit"]
        self.cpp_info.system_libs = ["dl"]
        self.cpp_info.set_property("cmake_file_name", "cppunit")
        self.cpp_info.set_property("cmake_target_name", "cppunit::cppunit")
        self.cpp_info.set_property("pkg_config_name", "cppunit")
