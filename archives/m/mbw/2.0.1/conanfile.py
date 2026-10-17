#!/usr/bin/env python3
"""Conan recipe for mbw 2 — Memory Bandwidth Benchmark (single C file, CMake).

mbw is a small command-line memory bandwidth benchmark (raas/mbw).  It builds
from a single mbw.c via CMake and installs one `mbw` executable.  No external
dependencies (only libc: stdio/stdlib/unistd/time/getopt).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy


class MbwConan(ConanFile):
    name = "mbw"
    version = "2.0.1"
    description = "Memory Bandwidth Benchmark (single C file, CMake)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/raas/mbw"
    url = "https://github.com/raas/mbw"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mbw is supported only on Linux/OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
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
        # Command-line tool: expose the bin dir for consumers.
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
