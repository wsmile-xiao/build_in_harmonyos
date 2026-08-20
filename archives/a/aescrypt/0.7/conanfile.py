#!/usr/bin/env python3
"""Conan recipe for aescrypt — AES (Rijndael) encryption/decryption command-line tool."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class AescryptConan(ConanFile):
    name = "aescrypt"
    version = "0.7"
    description = "Command-line tool for encrypting and decrypting files using the AES (Rijndael) block cipher"
    license = "BSD-4-Clause"
    homepage = "https://aescrypt.sourceforge.net"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # In-tree build: aescrypt's Makefile uses relative source paths
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # aescrypt's Makefile references source files by relative path,
        # so configure and make must run in the source directory
        self.run("./configure --prefix=/", env="conanbuild")
        self.run("make -j1", env="conanbuild")

    def package(self):
        # Makefile install target doesn't support DESTDIR; manually copy binaries
        copy(self, "aescrypt", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "aesget", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "tobin", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
