#!/usr/bin/env python3
"""Conan recipe for cahute 0.6 — CMake project (C language, ANSI C90).

Upstream: https://github.com/cahute/cahute (CeCILL 2.1 license)
Builds: static libcahute + CLI tools (p7, p7os, xfer9860).

Adaptation notes (OHOS aarch64):
- CAHUTE_LIBUSB=OFF: libusb/1.0.23 not published on ohpcd registry
  (optional feature; upstream also disables it on FXSDK/Amiga platforms).
- CAHUTE_SDL=OFF: p7screen (SDL-based screen viewer) not required for
  core library/CLI; sdl2 is published but feature left disabled in R01.
- CAHUTE_UDEV=OFF: udev rules not applicable on HarmonyOS.
- Patch 0001 adds <sys/select.h> and <sys/time.h> includes in
  lib/linkmedium.c (fd_set/struct timeval undeclared on OHOS).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CahuteConan(ConanFile):
    name = "cahute"
    version = "0.6"
    description = "Communication and file format handling tools for CASIO calculators"
    license = "CeCILL-2.1"
    homepage = "https://cahuteproject.org/"
    url = ""  # CI fills this

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
        tc.variables["CAHUTE_CLI"] = "ON"
        tc.variables["CAHUTE_LIBUSB"] = "OFF"
        tc.variables["CAHUTE_SDL"] = "OFF"
        tc.variables["CAHUTE_UDEV"] = "OFF"
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
        self.cpp_info.libs = ["cahute"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = [
            "include/cahute-0.6",
            "include",
        ]
