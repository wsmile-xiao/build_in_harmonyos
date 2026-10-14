#!/usr/bin/env python3
"""HarmonyOS OHAudio backend for RtAudio 6.0.1."""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class RtaudioConan(ConanFile):
    name = "rtaudio"
    version = "6.0.1.1"
    description = "RtAudio 6.0.1 with a native HarmonyOS OHAudio backend"
    license = "MIT"
    homepage = "https://github.com/thestk/rtaudio"
    package_type = "library"
    settings = "os", "compiler", "arch", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration("rtaudio/6.0.1.1 is the HarmonyOS OHAudio package")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["RTAUDIO_API_ALSA"] = False
        tc.variables["RTAUDIO_API_PULSE"] = False
        tc.variables["RTAUDIO_API_JACK"] = False
        tc.variables["RTAUDIO_API_OSS"] = False
        tc.variables["RTAUDIO_API_CORE"] = False
        tc.variables["RTAUDIO_API_DS"] = False
        tc.variables["RTAUDIO_API_ASIO"] = False
        tc.variables["RTAUDIO_API_WASAPI"] = False
        tc.variables["RTAUDIO_API_OHAUDIO"] = True
        tc.variables["RTAUDIO_BUILD_TESTING"] = False
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
        self.cpp_info.libs = ["rtaudio"]
        self.cpp_info.set_property("cmake_file_name", "RtAudio")
        self.cpp_info.set_property("cmake_target_name", "RtAudio::rtaudio")
        self.cpp_info.system_libs = ["ohaudio"]
