#!/usr/bin/env python3
"""Conan recipe — ympd 1.3.0 (CMake)."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class YmpdConan(ConanFile):
    name = "ympd"
    version = "1.3.0"
    description = "A lightweight web interface for the Music Player Daemon"
    license = "GPL-2.0-only"
    homepage = "https://github.com/notandy/ympd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libmpdclient/2.23")
        self.requires("openssl/3.5.8.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["WITH_DYNAMIC_ASSETS"] = "OFF"
        toolchain.variables["WITH_IPV6"] = "ON"
        toolchain.variables["WITH_SSL"] = "ON"

        mpd = self.dependencies["libmpdclient"].cpp_info
        openssl = self.dependencies["openssl"].cpp_info
        toolchain.variables["LIBMPDCLIENT_INCLUDE_DIR"] = mpd.includedirs[0]
        toolchain.variables["LIBMPDCLIENT_LIBRARY"] = (
            mpd.get_property("cmake_target_name") or "libmpdclient::libmpdclient"
        )
        toolchain.variables["OPENSSL_INCLUDE_DIR"] = openssl.includedirs[0]
        toolchain.variables["OPENSSL_LIBRARIES"] = (
            openssl.get_property("cmake_target_name") or "openssl::openssl"
        )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
