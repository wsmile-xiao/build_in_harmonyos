#!/usr/bin/env python3
"""Conan recipe — wildmidi 0.4.5

WildMIDI: soft MIDI synthesizer library (libwildmidi).
The upstream CMake build also offers an optional `wildmidi` player and dev
test tool; both require an audio backend (ALSA/OSS/OpenAL). None of these
exists on OHOS, so the library is built with WANT_PLAYER=OFF/WANT_DEVTEST=OFF.

Build system: CMake. License: LGPL-3.0-or-later.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class WildmidiConan(ConanFile):
    name = "wildmidi"
    version = "0.4.5"
    description = "WildMIDI — soft MIDI synthesizer library (libwildmidi)"
    license = "LGPL-3.0-or-later"
    homepage = "https://mindwerks.net/wildmidi/"
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

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.shared

    def source(self):
        # codeload URL carries no .tar.gz suffix; pin the filename so Conan
        # does not mistake the stream for a ZIP (§12.3)
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="wildmidi-0.4.5.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["WANT_STATIC"] = not self.options.shared
        # OHOS has no ALSA/OSS/OpenAL audio backends — build the library only
        tc.variables["WANT_PLAYER"] = False
        tc.variables["WANT_PLAYERSTATIC"] = False
        tc.variables["WANT_DEVTEST"] = False
        # Upstream declares cmake_minimum_required(3.1); CMake >= 4 rejects it
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # must be a -D on the cmake command line (toolchain-file set() is too
        # late for CMake 4's compatibility check at cmake_minimum_required())
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # upstream CMake names the library libWildMidi (LIBRARY_DYN_NAME /
        # LIBRARY_STATIC_NAME); declare the real artifact name
        self.cpp_info.libs = ["WildMidi"]
