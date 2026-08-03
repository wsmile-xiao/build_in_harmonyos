#!/usr/bin/env python3
"""Conan recipe for openal-soft 1.25.2 — CMake project.

OpenAL Soft is an open-source, cross-platform 3D audio API implementation
(LGPL-2.0-or-later).

OHOS / probe notes:
- CMake backend options: all external audio backends (ALSA, PulseAudio,
  PipeWire, JACK, OSS, Solaris, SndIO, PortAudio, SDL2, SDL3, WaveFile,
  Oboe, OpenSL, CoreAudio) are disabled; only the built-in Null/loopback
  backends remain, so the package does not depend on real audio devices.
- Upstream tests (ALSOFT_TESTS) are disabled in the production build; they
  require GoogleTest via FetchContent and are exercised separately in the
  probe. GoogleTest is NOT a production dependency.
- fmt-11.2.0 and gsl are bundled in the source tree (add_subdirectory
  fmt-11.2.0 EXCLUDE_FROM_ALL; gsl is header-only).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class OpenALSoftConan(ConanFile):
    name = "openal-soft"
    version = "1.25.2"
    description = "OpenAL Soft — open-source cross-platform 3D audio API (LGPL)"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/kcat/openal-soft"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS: CMake does not recognize the HarmonyOS platform; treat as
        # Linux/aarch64 for configure-time checks (E092 pattern).
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # ---- minimal core build: no utils/examples/tests/dlopen/modules ----
        tc.cache_variables["ALSOFT_UTILS"] = "OFF"
        tc.cache_variables["ALSOFT_EXAMPLES"] = "OFF"
        tc.cache_variables["ALSOFT_TESTS"] = "OFF"
        tc.cache_variables["ALSOFT_DLOPEN"] = "OFF"
        tc.cache_variables["ALSOFT_ENABLE_MODULES"] = "OFF"
        tc.cache_variables["ALSOFT_BACKEND_WAVE"] = "OFF"

        # ---- all external audio backends disabled ----
        for backend in ("ALSA", "PULSEAUDIO", "PIPEWIRE", "JACK", "OSS",
                        "SOLARIS", "SNDIO", "PORTAUDIO", "SDL2", "SDL3",
                        "OBOE", "OPENSL", "COREAUDIO"):
            tc.cache_variables[f"ALSOFT_BACKEND_{backend}"] = "OFF"

        # NOTE: probe workarounds (compat-inc shims, FORCE_FMT, 8 compile
        # patches) are NOT part of the formal recipe — they live under
        # $HOME/tmp/openal-1.25.2-reports/probe-patches and are probe-only.
        # The formal recipe therefore does NOT carry any absolute temp paths.
        # Until OHOS libc++/Clang 15 compatibility fixes are provided as
        # reviewable formal patches, this recipe is NOT reproducible on a
        # clean OHOS toolchain (see notes.md).
        tc.cache_variables["CMAKE_CXX_FLAGS"] = "-D_LIBCPP_ENABLE_EXPERIMENTAL"
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
        self.cpp_info.libs = ["openal"]
        self.cpp_info.set_property("cmake_target_name", "OpenAL::OpenAL")
