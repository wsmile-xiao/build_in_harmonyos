#!/usr/bin/env python3
"""Conan recipe for OpenAL Soft 1.24.1.

OpenAL Soft is the portable reference implementation of the OpenAL 3D audio
API (LGPL-2.0-or-later, https://openal-soft.org/).

OHOS notes:
- Built as a static library (``LIBTYPE=STATIC``).  OHOS ships no system
  libopenal, so a static package avoids any SONAME clash with ``/lib``.
- Every external audio backend (ALSA / PipeWire / PulseAudio / JACK / OSS /
  Solaris / SndIO / PortAudio / SDL2 / Oboe / OpenSL / CoreAudio / Wave
  writer) is disabled.  Only the two backends that upstream always builds
  (null and loopback) remain, so the package needs no audio device at build
  or test time.
- Utilities, examples, upstream tests (GoogleTest via FetchContent), runtime
  ``dlopen`` probing and the optional install-time data sets are all disabled;
  the vendored ``fmt-11.0.2`` is still compiled from the source tree
  (``add_subdirectory(... EXCLUDE_FROM_ALL)``) because the core needs it.
- The upstream release only requires C++17, which is exactly what the OHOS
  clang 15 / libc++ toolchain provides, so no C++20 std-library shim is needed.
"""
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
    version = "1.24.1"
    description = "Software implementation of the OpenAL 3D audio API"
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
            # Static only: no system libopenal on OHOS to clash with.
            "LIBTYPE": "STATIC",
            # No runtime library probing / module loading.
            "ALSOFT_DLOPEN": False,
            "ALSOFT_UTILS": False,
            "ALSOFT_NO_CONFIG_UTIL": True,
            "ALSOFT_EXAMPLES": False,
            "ALSOFT_TESTS": False,
            "ALSOFT_UPDATE_BUILD_VERSION": False,
            "ALSOFT_INSTALL_CONFIG": False,
            "ALSOFT_INSTALL_HRTF_DATA": False,
            "ALSOFT_INSTALL_AMBDEC_PRESETS": False,
            "ALSOFT_INSTALL_EXAMPLES": False,
            "ALSOFT_INSTALL_UTILS": False,
            "ALSOFT_EMBED_HRTF_DATA": False,
            "ALSOFT_SEARCH_INSTALL_DATADIR": False,
            "ALSOFT_EAX": False,
            # Null + loopback are always built and need no device.
            "ALSOFT_BACKEND_ALSA": False,
            "ALSOFT_BACKEND_PIPEWIRE": False,
            "ALSOFT_BACKEND_PULSEAUDIO": False,
            "ALSOFT_BACKEND_JACK": False,
            "ALSOFT_BACKEND_OSS": False,
            "ALSOFT_BACKEND_SOLARIS": False,
            "ALSOFT_BACKEND_SNDIO": False,
            "ALSOFT_BACKEND_PORTAUDIO": False,
            "ALSOFT_BACKEND_SDL2": False,
            "ALSOFT_BACKEND_COREAUDIO": False,
            "ALSOFT_BACKEND_OBOE": False,
            "ALSOFT_BACKEND_OPENSL": False,
            "ALSOFT_BACKEND_WAVE": False,
            # x86 CPU extension probes stay off (aarch64 target).
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
