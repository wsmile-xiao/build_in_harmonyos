#!/usr/bin/env python3
"""Conan recipe — rtmidi 6.0.0 (C++ realtime MIDI I/O, CMake).

RtMidi provides realtime MIDI input/output across Linux(ALSA/JACK),
macOS(CoreMIDI), Windows(MM/UWP), Web MIDI and Android(AMIDI). On targets
with none of those subsystems (HarmonyOS/OHOS PC has no MIDI backend) the
upstream header auto-defines __RTMIDI_DUMMY__ (RtMidi.cpp:88-90) and the
library builds with a compilable-but-non-functional dummy API — this
adaptation verifies that fallback end to end (upstream apinames + consumer
checks) instead of silently shipping an unverified zero-API build.

Upstream "tests" are demo programs; apinames.cpp is the only one with real
assertions (compiled-API name mapping). It runs in build() (R51, CI L1c).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class RtmidiConan(ConanFile):
    name = "rtmidi"
    version = "6.0.0"
    description = "Realtime MIDI input/output C++ library (dummy-API fallback verified on OHOS)"
    license = "RTMIDI license (MIT-like)"
    homepage = "https://github.com/thestk/rtmidi"
    url = "https://github.com/thestk/rtmidi"
    topics = ("midi", "audio", "music", "cpp11")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["RTMIDI_BUILD_TESTING"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream test entry points (R51): apinames has real assertions on
        # compiled-API name mapping; testcapi exercises the C wrapper.
        tests = os.path.join(self.build_folder, "tests")
        self.run(f'"{os.path.join(tests, "apinames")}"', env="conanbuild")
        self.run(f'"{os.path.join(tests, "testcapi")}"', env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # The upstream-installed CMake config collides with the CMakeDeps
        # generated one (two rtmidi-config.cmake); keep Conan as the single
        # package-config surface and drop upstream's bundled configs.
        for d in ("lib/cmake", "share/cmake", "share/rtmidi", "share/pkgconfig", "lib/pkgconfig"):
            shutil.rmtree(os.path.join(self.package_folder, d), ignore_errors=True)

    def package_info(self):
        self.cpp_info.libs = ["rtmidi"]
        # upstream installs headers into include/rtmidi/; expose both roots
        self.cpp_info.includedirs = ["include", "include/rtmidi"]
        self.cpp_info.set_property("cmake_file_name", "rtmidi")
        self.cpp_info.set_property("cmake_target_name", "rtmidi::rtmidi")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
