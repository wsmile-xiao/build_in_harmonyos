#!/usr/bin/env python3
"""Conan recipe — pciutils 3.13.0 (Makefile-based build system)"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class PciutilsConan(ConanFile):
    name = "pciutils"
    version = "3.13.0"
    description = "PCI bus configuration and inspection utilities (lspci, setpci, pcilmr)"
    license = "GPL-2.0-or-later"
    homepage = "https://mj.ucw.cz/sw/pciutils/"

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
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        shared_flag = "yes" if self.options.shared else "no"
        self.run(f"make -j1 SHARED={shared_flag}", cwd=self.source_folder, env="conanbuild")

    def package(self):
        shared_flag = "yes" if self.options.shared else "no"
        self.run(
            f'make install install-lib PREFIX="{self.package_folder}" DESTDIR="" SHARED={shared_flag}',
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package_info(self):
        self.cpp_info.libs = ["pci"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin", "sbin"]
