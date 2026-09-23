#!/usr/bin/env python3
"""Conan recipe - polyseed 1.0.0 (CMake build, pure C library).

polyseed is a 16-word mnemonic seed library for Monero and other
CryptoNote-based currencies. It has no third-party link dependencies:
crypto/UTF-8 services are supplied by the embedder at runtime through
polyseed_inject() dependency injection.
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
)


class PolyseedConan(ConanFile):
    name = "polyseed"
    version = "1.0.0"
    description = (
        "Mnemonic seed library for Monero and other CryptoNote-based currencies"
    )
    license = "LGPL-3.0-only"
    homepage = "https://github.com/tevador/polyseed"
    topics = ("monero", "cryptonote", "mnemonic", "seed")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The upstream word lookup and UTF-8 fast paths detect non-ASCII
        # bytes with `*p < 0` on plain `char`. The AArch64 ELF ABI makes
        # `char` unsigned by default (CHAR_MIN=0), which silently disables
        # those branches and breaks round-trips for non-ASCII languages;
        # force signed char so behaviour matches the x86-64 reference.
        tc.extra_cflags.append("-fsigned-char")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream ships its suite as the `polyseed-tests` target (tests/tests.c,
        # 51 cases) but never registers it with CTest, so run it directly.
        matches = glob.glob(
            os.path.join(self.build_folder, "**", "polyseed-tests"), recursive=True
        )
        assert matches, "polyseed-tests executable not found after cmake.build()"
        self.run(f'"{matches[0]}"')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream CMakeLists always builds and installs BOTH libpolyseed.so
        # and libpolyseed.a; keep only the artifact matching the `shared`
        # option so consumers link exactly what they requested.
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            rm(self, "libpolyseed.a", libdir)
        else:
            rm(self, "libpolyseed.so*", libdir)

    def package_info(self):
        self.cpp_info.libs = ["polyseed"]
        self.cpp_info.set_property("cmake_file_name", "polyseed")
        self.cpp_info.set_property("cmake_target_name", "polyseed::polyseed")
