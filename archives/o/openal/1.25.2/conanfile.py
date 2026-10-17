#!/usr/bin/env python3
"""Conan recipe for OpenAL Soft 1.25.2."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class OpenalConan(ConanFile):
    name = "openal"
    version = "1.25.2"
    description = "Cross-platform OpenAL audio implementation"
    license = "LGPL-2.0-or-later"
    homepage = "https://openal-soft.org/"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("openal supports Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        arch = str(self.settings.arch)
        variables = {
            "LIBTYPE": "STATIC",
            "ALSOFT_DLOPEN": False,
            "ALSOFT_DLOPEN_NOTES": False,
            "ALSOFT_UTILS": False,
            "ALSOFT_EXAMPLES": False,
            "ALSOFT_TESTS": False,
            "ALSOFT_INSTALL_CONFIG": False,
            "ALSOFT_INSTALL_HRTF_DATA": False,
            "ALSOFT_INSTALL_AMBDEC_PRESETS": False,
            "ALSOFT_INSTALL_EXAMPLES": False,
            "ALSOFT_INSTALL_UTILS": False,
            "ALSOFT_UPDATE_BUILD_VERSION": False,
            "ALSOFT_EAX": False,
            "ALSOFT_ENABLE_MODULES": False,
            "ALSOFT_EMBED_HRTF_DATA": False,
            "ALSOFT_BACKEND_PIPEWIRE": False,
            "ALSOFT_BACKEND_PULSEAUDIO": False,
            "ALSOFT_BACKEND_ALSA": False,
            "ALSOFT_BACKEND_OSS": False,
            "ALSOFT_BACKEND_SOLARIS": False,
            "ALSOFT_BACKEND_SNDIO": False,
            "ALSOFT_BACKEND_JACK": False,
            "ALSOFT_BACKEND_COREAUDIO": False,
            "ALSOFT_BACKEND_OBOE": False,
            "ALSOFT_BACKEND_OPENSL": False,
            "ALSOFT_BACKEND_PORTAUDIO": False,
            "ALSOFT_BACKEND_SDL2": False,
            "ALSOFT_BACKEND_SDL3": False,
            "ALSOFT_BACKEND_WAVE": False,
            "ALSOFT_CPUEXT_SSE": False,
            "ALSOFT_CPUEXT_SSE2": False,
            "ALSOFT_CPUEXT_SSE3": False,
            "ALSOFT_CPUEXT_SSE4_1": False,
            "ALSOFT_CPUEXT_NEON": arch.startswith(("armv8", "armv9")),
        }
        for name, value in variables.items():
            toolchain.variables[name] = value
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["openal"]
        self.cpp_info.defines = ["AL_LIBTYPE_STATIC"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "OpenAL")
        self.cpp_info.set_property("cmake_target_name", "OpenAL::OpenAL")
