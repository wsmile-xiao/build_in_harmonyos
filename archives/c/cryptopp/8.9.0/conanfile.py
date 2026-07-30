#!/usr/bin/env python3
"""Conan recipe for Crypto++ (cryptopp) 8.9.0 — static library build."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CryptoppConan(ConanFile):
    name = "cryptopp"
    version = "8.9.0"
    description = "C++ cryptographic algorithm library"
    license = "BSL-1.0"
    homepage = "https://www.cryptopp.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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

    def build(self):
        apply_conandata_patches(self)

        # Crypto++ uses CXX (C++ compiler)
        # R33: Get compiler from Conan conf, NEVER from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++")

        # R9: Always use -j1, never -j$(nproc)
        # P3 fix: quote CXX path in case it contains spaces
        if self.options.shared:
            self.run(f'make dynamic CXX="{cxx}" -j1', cwd=self.source_folder)
        else:
            self.run(f'make CXX="{cxx}" -j1', cwd=self.source_folder)

    def package(self):
        # Crypto++ headers go to include/cryptopp/
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include", "cryptopp"))
        if self.options.shared:
            copy(self, "libcryptopp.so*", self.source_folder, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libcryptopp.a", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["cryptopp"]
