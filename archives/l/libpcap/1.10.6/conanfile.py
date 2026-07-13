#!/usr/bin/env python3
"""Conan recipe for libpcap 1.10.6 — Packet capture library.

Build system: cmake.
Patches: config.guess/config.sub OHOS detection, pcap-linux.c sockaddr_storage fix.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibpcapConan(ConanFile):
    name = "libpcap"
    version = "1.10.6"
    description = "Packet capture library"
    license = "BSD-3-Clause"
    homepage = "https://www.tcpdump.org/"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/l/libpcap/1.10.6"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        self.cpp_info.libs = ["pcap"]
