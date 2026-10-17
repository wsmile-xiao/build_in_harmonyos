#!/usr/bin/env python3
"""Conan recipe — asahi-scripts 20250713

Pure shell-script project with Makefile build system.
No compilation step; Makefile's `all` target uses sed to process scripts,
`install` target copies scripts and functions.sh to system directories.

Product: executable shell scripts (asahi-diagnose, asahi-fwupdate, update-m1n1)
         + shared functions library (functions.sh)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AsahiScriptsConan(ConanFile):
    name = "asahi-scripts"
    version = "20250713"
    description = "Asahi Linux reference distro management scripts (diagnostics, firmware update, first-boot, GRUB/m1n1 updates)"
    license = "MIT"
    homepage = "https://github.com/AsahiLinux/asahi-scripts"
    url = ""  # CI fills this

    package_type = "application"

    # R32: settings.os compatible with both Linux and OHOS
    # CI L0p requires all four settings items even for shell-only packages
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Build scripts: Makefile `all` target uses sed to process scripts.
        # Must run from source_folder because basic_layout may use a build subfolder.
        # R33: No CC/CFLAGS needed — pure shell, no compilation
        # R9: Use -j1
        self.run(f"make -C {self.source_folder} all -j1")

    def package(self):
        # Copy built scripts from source_folder/build/ to bin/
        # Makefile `all` target creates build/ with sed-processed scripts
        build_dir = os.path.join(self.source_folder, "build")
        copy(self, "asahi-diagnose", build_dir,
             os.path.join(self.package_folder, "bin"))
        copy(self, "asahi-fwupdate", build_dir,
             os.path.join(self.package_folder, "bin"))
        copy(self, "update-m1n1", build_dir,
             os.path.join(self.package_folder, "bin"))
        # functions.sh is NOT processed by `all` target — copy from source folder
        # Scripts check $(dirname $0)/functions.sh first, so put in bin/
        copy(self, "functions.sh", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        # Also install to share/asahi-scripts/ (standard path fallback)
        copy(self, "functions.sh", self.source_folder,
             os.path.join(self.package_folder, "share", "asahi-scripts"))

    def package_info(self):
        # Executable scripts package — expose bin/ directory
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
