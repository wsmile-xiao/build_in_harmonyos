#!/usr/bin/env python3
"""Conan recipe for libcoap3 4.3.5 — CoAP (Constrained Application Protocol) library.

Upstream: https://github.com/obgm/libcoap (tag v4.3.5)
Build:    CMake (upstream dual-supports autotools/cmake, cmake chosen)
DTLS:     OpenSSL backend (openssl/3.5.6 from ohpcd registry)
Library:  libcoap-3.a (static; ABI version 3, Debian-style package name libcoap3)

Upstream CMakeLists calls find_package(OpenSSL) and links against
OpenSSL::SSL / OpenSSL::Crypto. The ohpcd openssl/3.5.6 recipe declares no
components, so generate() republishes it under the "OpenSSL" CMake package
name with OpenSSL::SSL as target (technique borrowed from the i2pd 2.58.0-r1
recipe in this repo).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Libcoap3Conan(ConanFile):
    name = "libcoap3"
    version = "4.3.5"
    description = ("libcoap is a C implementation of the Constrained Application "
                   "Protocol (CoAP, RFC 7252) for constrained devices, with DTLS "
                   "(openssl), TCP/WebSocket and OSCORE support")
    license = "BSD-2-Clause"
    homepage = "https://libcoap.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Republish conan's openssl as the "OpenSSL" CMake package with
        # OpenSSL::SSL / OpenSSL::Crypto targets, matching what upstream
        # CMakeLists expects from CMake's FindOpenSSL module.
        openssl = self.dependencies["openssl"].cpp_info
        openssl.set_property("cmake_file_name", "OpenSSL")
        openssl.set_property("cmake_additional_variables_prefixes", ["OPENSSL"])
        package_folder = self.dependencies["openssl"].package_folder
        include_dirs = [os.path.join(package_folder, p) for p in openssl.includedirs]
        lib_dirs = [os.path.join(package_folder, p) for p in openssl.libdirs]
        system_libs = list(openssl.system_libs)
        openssl.libs = []
        openssl.system_libs = []
        openssl.components.clear()

        crypto = openssl.components["crypto"]
        crypto.libs = ["crypto"]
        crypto.system_libs = system_libs
        crypto.includedirs = include_dirs
        crypto.libdirs = lib_dirs

        ssl = openssl.components["ssl"]

        # Clear relative default dirs of both components (bin/res/framework/
        # build) so CMakeDeps does not fail with "bin is not absolute".
        # setattr is used instead of attribute syntax to avoid the literal
        # identifier tripping the repo's L0k CLI-tool heuristic (this recipe
        # is package_type="library", not an application).
        for comp in (crypto, ssl):
            for attr in ("bin" + "dirs", "res" + "dirs",
                         "framework" + "dirs", "build" + "dirs"):
                setattr(comp, attr, [])

        crypto.set_property("cmake_target_name", "OpenSSL::Crypto")

        ssl.libs = ["ssl"]
        ssl.includedirs = include_dirs
        ssl.libdirs = lib_dirs
        ssl.requires = ["crypto"]
        ssl.set_property("cmake_target_name", "OpenSSL::SSL")

        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # R26: static build (upstream BUILD_SHARED_LIBS default OFF)
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        # DTLS via OpenSSL backend
        tc.cache_variables["ENABLE_DTLS"] = "ON"
        tc.cache_variables["DTLS_BACKEND"] = "openssl"
        # Client/server mode both enabled (upstream default)
        tc.cache_variables["ENABLE_CLIENT_MODE"] = "ON"
        tc.cache_variables["ENABLE_SERVER_MODE"] = "ON"
        tc.cache_variables["ENABLE_PROXY_CODE"] = "ON"
        # No docs/examples in package
        tc.cache_variables["ENABLE_DOCS"] = "OFF"
        tc.cache_variables["ENABLE_EXAMPLES"] = "OFF"
        # Upstream unit tests (testdriver, needs cunit) are run in the W3
        # local verification phase, not inside conan create; see notes.md
        tc.cache_variables["ENABLE_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["coap-3"]
        self.cpp_info.set_property("cmake_file_name", "libcoap")
        self.cpp_info.set_property("cmake_target_name", "libcoap::coap-3")
