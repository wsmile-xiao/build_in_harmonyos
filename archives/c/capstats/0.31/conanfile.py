#!/usr/bin/env python3
"""Conan recipe for capstats 0.31."""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class CapstatsConan(ConanFile):
    name = "capstats"
    version = "0.31"
    description = "NIC traffic statistics collector using libpcap"
    license = "BSD-3-Clause"
    homepage = "https://github.com/zeek/capstats"
    url = "https://github.com/zeek/capstats"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # The upstream CMake module uses find_path/find_library directly and
        # does not consume Conan's generated package config. Point it at the
        # exact libpcap package folder so PCAP_ROOT_DIR resolves on OHOS.
        tc.cache_variables["PCAP_ROOT_DIR"] = self.dependencies.host["libpcap"].package_folder
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # capstats has no upstream test target. Invoke CTest directly so the
        # empty upstream suite is still exercised and reported instead of
        # asking the generator for a non-existent `test` build target.
        self.run(
            f'ctest --test-dir "{self.build_folder}" --output-on-failure'
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
