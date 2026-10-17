#!/usr/bin/env python3
"""Conan recipe for p7zip 17.05 — makefile-based command-line archiver tool."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class P7ZipConan(ConanFile):
    name = "p7zip"
    version = "17.05"
    description = "7-Zip file archiver with high compression ratio (POSIX port)"
    license = "LGPL-2.1-or-later"
    homepage = "https://p7zip.sourceforge.net/"
    # CI fills url from remote

    package_type = "application"

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
        # p7zip uses root makefile which includes makefile.common -> makefile.machine
        # Build 7z (console with external codecs) and 7za (standalone)
        self.run("make 7z 7za", cwd=self.source_folder)

    def package(self):
        # Copy binaries directly to bin/ (install.sh creates wrapper scripts
        # with /bin/sh shebang that doesn't work on HarmonyOS)
        copy(self, "7z", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "7za", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "7z.so", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "lib", "p7zip"))
        copy(self, "*.so", src=os.path.join(self.source_folder, "bin", "Codecs"),
             dst=os.path.join(self.package_folder, "lib", "p7zip", "Codecs"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/p7zip"]
