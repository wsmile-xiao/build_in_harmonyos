#!/usr/bin/env python3
"""Conan recipe for audaspace 1.5.0 — High-level audio library (Blender)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AudaspaceConan(ConanFile):
    name = "audaspace"
    version = "1.5.0"
    description = "Audaspace is a high-level audio library written in C++ (used by Blender)"
    license = "Apache-2.0"
    homepage = "https://github.com/neXyon/audaspace"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

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
        # audaspace uses SHARED_LIBRARY (not BUILD_SHARED_LIBS) to control SHARED vs STATIC
        shared = "ON" if self.options.shared else "OFF"
        tc.variables["SHARED_LIBRARY"] = shared
        tc.variables["BUILD_SHARED_LIBS"] = shared
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Minimal deps for OHOS: disable all optional heavy dependencies
        tc.variables["WITH_FFMPEG"] = False
        tc.variables["WITH_FFTW"] = False
        tc.variables["WITH_JACK"] = False
        tc.variables["WITH_LIBSNDFILE"] = False
        tc.variables["WITH_OPENAL"] = False
        tc.variables["WITH_SDL"] = False
        tc.variables["WITH_PULSEAUDIO"] = False
        tc.variables["WITH_PYTHON"] = False
        tc.variables["WITH_DOCS"] = False
        tc.variables["BUILD_DEMOS"] = False
        tc.variables["WITH_C"] = True
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
        self.cpp_info.libs = ["audaspace", "audaspace-c"]
        # E247: static archive contains C++ objects behind C API, must propagate C++ runtime
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m", "c++"]
        else:
            self.cpp_info.system_libs = ["pthread", "m"]
