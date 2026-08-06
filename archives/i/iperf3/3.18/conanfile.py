#!/usr/bin/env python3
"""Conan recipe for iperf3 3.18 — network bandwidth testing tool (CMake).

iperf3 is a command-line tool for measuring TCP/UDP/SCTP bandwidth.
Built with CMake using the provided CMakeLists.txt patch (autotools
config.status fails on HarmonyOS due to HMDFS temp-file restrictions).

Patches:
  0001-CMakeLists.txt         — CMake build system (replaces autotools)
  0002-pthread_stubs.c       — Stubs for pthread_cancel etc. (not in OHOS libc)
  0003-iperf3.spec           — RPM spec (metadata only)
  0004-config.guess          — OHOS platform recognition (autotools fallback)
  0005-config.sub            — OHOS platform recognition (autotools fallback)
  0006-iperf_config.h        — Pre-generated config header
  0007-version.h             — Version string header
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Iperf3Conan(ConanFile):
    name = "iperf3"
    version = "3.18"
    description = "Network bandwidth testing tool (TCP/UDP/SCTP)"
    license = "BSD-3-Clause"
    homepage = "https://software.es.net/iperf/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: os check must include OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        # Apply patches manually using 'patch' command
        # (Conan's apply_conandata_patches uses git apply which fails on new-file patches
        #  with --- a/filename format; the 'patch' command handles this correctly)
        patches = self.conan_data.get("patches", [])
        for patch_info in patches:
            patch_file = patch_info["patch_file"]
            patch_path = os.path.join(self.source_folder, patch_file)
            if os.path.exists(patch_path):
                self.run(f'patch -p1 -i "{patch_path}"',
                         cwd=self.source_folder)
            else:
                raise ConanException(f"Patch file not found: {patch_path}")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # iperf3 is a command-line tool, no libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
