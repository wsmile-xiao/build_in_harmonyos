#!/usr/bin/env python3
"""Conan recipe for rtaudio 6.0.1 — realtime audio I/O C++ library.

OHOS platform boundary: the system has no ALSA/JACK/Pulse/OSS audio stack,
so every RTAUDIO_API_* option is explicitly OFF. RtAudio.h then auto-defines
__RTAUDIO_DUMMY__ ("a compilable but non-functional API"): the library
compiles and links cleanly, enumerates zero devices at runtime, and real
audio I/O is a documented platform boundary (see notes.md / draft E2176).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class RtaudioConan(ConanFile):
    name = "rtaudio"
    version = "6.0.1"
    description = "Realtime audio I/O C++ classes; OHOS 适配为 __RTAUDIO_DUMMY__ 后端（无音频栈平台，编译/链接完整、运行期音频 I/O 为平台边界）"
    license = "MIT"
    homepage = "https://github.com/thestk/rtaudio"

    package_type = "library"
    settings = "os", "compiler", "arch", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 无 ALSA/JACK/Pulse/OSS/WASAPI/Core 后端：全部显式关闭，
        # RtAudio.h 自动定义 __RTAUDIO_DUMMY__（可编译不可运行的桩后端）
        tc.variables["RTAUDIO_API_ALSA"] = False
        tc.variables["RTAUDIO_API_PULSE"] = False
        tc.variables["RTAUDIO_API_JACK"] = False
        tc.variables["RTAUDIO_API_OSS"] = False
        tc.variables["RTAUDIO_API_CORE"] = False
        tc.variables["RTAUDIO_API_DS"] = False
        tc.variables["RTAUDIO_API_ASIO"] = False
        tc.variables["RTAUDIO_API_WASAPI"] = False
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
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = []
