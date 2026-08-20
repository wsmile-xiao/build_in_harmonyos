#!/usr/bin/env python3
"""Conan recipe — stuntman 1.2.16 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, Autotools
from conan.tools.layout import basic_layout


class StuntmanConan(ConanFile):
    name = "stuntman"
    version = "1.2.16"
    description = "Open source STUN protocol implementation providing STUN server and client"
    license = "Apache-2.0"
    homepage = "https://www.stunprotocol.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")
        # Boost headers only (shared_ptr, scoped_array, scoped_ptr, crc, property_tree)
        self.requires("boost/1.91.0", headers=True, libs=False)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS: lld requires libxml2.so.16 (unavailable), use GNU ld
        # Also add openssl lib path for -lcrypto (GNU ld doesn't search Conan dirs)
        openssl_pkg = self.dependencies["openssl"].package_folder
        tc.extra_ldflags.append(f"-fuse-ld=ld -L{openssl_pkg}/lib")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Set BOOST_INCLUDE and OPENSSL_INCLUDE (used by subdirectory Makefiles
        # in their INCLUDES := $(BOOST_INCLUDE) $(OPENSSL_INCLUDE) -I../common ...)
        # env="conanbuild" provides CC, CXX, LDFLAGS with -fuse-ld=ld and lib paths
        boost_pkg = self.dependencies["boost"].package_folder
        openssl_pkg = self.dependencies["openssl"].package_folder
        self.run(
            f'make -C "{self.source_folder}"'
            f' BOOST_INCLUDE="-I{boost_pkg}/include"'
            f' OPENSSL_INCLUDE="-I{openssl_pkg}/include"'
            f' -j1',
            env="conanbuild"
        )

    def package(self):
        # stuntman Makefile has no install target; manually copy binaries
        copy(self, "stunserver", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "stunclient", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "stuntestcode", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # stuntman is a standalone binary tool, no libraries to export
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
