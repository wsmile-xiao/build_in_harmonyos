#!/usr/bin/env python3
"""Conan recipe for vo-amrwbenc — VisualOn AMR-WB encoder library.

Autotools static-library package, modeled on the merged vo-aacenc/0.1.3
precedent (same upstream project family and era).
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class VoAmrwbencConan(ConanFile):
    name = "vo-amrwbenc"
    version = "0.1.3"
    description = "VisualOn AMR-WB audio encoder library"
    license = "Apache-2.0"
    homepage = "https://opencore-amr.sourceforge.net/"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("vo-amrwbenc is packaged for OHOS armv8 only")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--disable-shared", "--enable-static"])
        # Upstream's 2010-era config.sub rejects the newer linux-ohos triplet.
        tc.configure_args.extend(["--build=aarch64-unknown-linux-gnu", "--host=aarch64-unknown-linux-gnu"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: mktemp temp dir under umask 077 becomes unwritable for
        # config.status (knowledge E011/E114) — relax (vo-aacenc precedent).
        replace_in_file(self, f"{self.source_folder}/configure", "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "NOTICE", src=self.source_folder, dst=f"{self.package_folder}/licenses")

    def package_info(self):
        self.cpp_info.libs = ["vo-amrwbenc"]
        self.cpp_info.set_property("cmake_file_name", "vo-amrwbenc")
        self.cpp_info.set_property("cmake_target_name", "vo-amrwbenc::vo-amrwbenc")
        self.cpp_info.set_property("pkg_config_name", "vo-amrwbenc")
