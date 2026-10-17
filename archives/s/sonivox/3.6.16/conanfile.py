#!/usr/bin/env python3
"""Conan recipe — sonivox 3.6.16 (CMake, fork of AOSP platform_external_sonivox).

Builds the EAS wavetable MIDI synthesizer library (static or shared) and,
optionally, the upstream `sonivoxrender` CLI (SMF MIDI -> raw PCM on stdout).
The upstream 3.6.16 sources compile unmodified with the OHOS SDK clang 15
toolchain, so this recipe ships without patches.

BUILD_TESTING is forced OFF for the packaged build: with tests enabled the
upstream CMake configure step downloads an 81 MB DLS soundfont and fetches
GoogleTest from GitHub, which would make `conan create` non-hermetic. The
upstream suite (33 cases) is executed separately during adaptation
verification; see notes.md and test_package/MANIFEST.yml for the evidence.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os

required_conan_version = ">=2.0"


class SonivoxConan(ConanFile):
    name = "sonivox"
    version = "3.6.16"
    description = "Sonivox EAS embedded wavetable MIDI synthesizer (AOSP fork with CMake build)"
    license = "Apache-2.0"
    homepage = "https://github.com/pedrolcl/sonivox"
    url = "https://github.com/pedrolcl/sonivox"
    topics = ("midi", "synthesizer", "audio", "eas", "wavetable")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "example": [True, False]}
    default_options = {"shared": False, "example": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_EXAMPLE"] = bool(self.options.example)
        tc.variables["BUILD_MANPAGE"] = False
        tc.variables["BUILD_SONIVOX_STATIC"] = not self.options.shared
        tc.variables["BUILD_SONIVOX_SHARED"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["sonivox"] if self.options.shared else ["sonivox-static"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "sonivox")
