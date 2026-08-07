#!/usr/bin/env python3
"""Conan recipe for libssh 0.11.4 — CMake build system.

libssh is an SSH client/server library using OpenSSL as crypto backend.
Built as static library by default (zlib dependency not compiled with -fPIC).

Dependencies:
  - openssl/1.1.1w (crypto backend)
  - zlib/1.3.1 (compression)

Patch: conan-target-aliases.patch — creates standard CMake target aliases
(ZLIB::ZLIB, OpenSSL::Crypto) so libssh's CMakeLists.txt can find Conan-provided
targets which use lowercase naming (zlib::zlib, openssl::openssl).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibsshConan(ConanFile):
    name = "libssh"
    version = "0.11.4"
    description = "SSH client/server library"
    license = "LGPL-2.1"
    homepage = "https://www.libssh.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Static build by default (zlib not built with -fPIC for shared linking)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # Enable all features — no trimming
        tc.variables["WITH_ZLIB"] = True
        tc.variables["WITH_SFTP"] = True
        tc.variables["WITH_SERVER"] = True
        tc.variables["WITH_EXAMPLES"] = False  # Examples not needed in Conan package
        tc.variables["WITH_PCAP"] = True
        tc.variables["WITH_GEX"] = True
        tc.variables["WITH_EXEC"] = True
        tc.variables["WITH_GSSAPI"] = True
        tc.variables["WITH_NACL"] = True
        tc.variables["UNIT_TESTING"] = False  # CMocka not available on OHOS
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ssh"]
        self.cpp_info.set_property("cmake_file_name", "libssh")
        self.cpp_info.set_property("cmake_target_name", "libssh::libssh")
        self.cpp_info.set_property("pkg_config_name", "libssh")
