#!/usr/bin/env python3
"""Conan recipe — webrtc-audio-processing-2 2.1 (meson)

WebRTC Audio Processing Library — standalone extraction of WebRTC's
audio processing module, maintained by PulseAudio team.

Source: https://gitlab.freedesktop.org/pulseaudio/webrtc-audio-processing
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, collect_libs
from conan.tools.meson import Meson, MesonToolchain, meson_layout


class WebrtcAudioProcessing2Conan(ConanFile):
    name = "webrtc-audio-processing-2"
    version = "2.1"
    description = "WebRTC Audio Processing Library (standalone, from PulseAudio team)"
    license = "BSD-3-Clause"
    homepage = "https://gitlab.freedesktop.org/pulseaudio/webrtc-audio-processing"
    url = ""

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpulseaudio/16.1")
        self.requires("speexdsp/1.2.1")

    def layout(self):
        meson_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.compile()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "webrtc-audio-processing-2")
        self.cpp_info.set_property("cmake_target_name", "webrtc-audio-processing-2::webrtc-audio-processing-2")
