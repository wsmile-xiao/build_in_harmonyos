#!/usr/bin/env python3
"""Conan recipe — Snapcast (Multiroom client-server audio player).

Build system: CMake
Dependencies: alsa-lib, boost, flac, libvorbis, libogg, opus, libsoxr, openssl, expat

Snapcast produces two executables: snapserver and snapclient.
Avahi (mDNS service discovery) is disabled because avahi-client is not available
in the OHOS Conan registry. Tremor is disabled (OFF by default upstream),
libvorbis provides Vorbis support instead.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import Environment


OHOS_COMPAT_H = """// OpenHarmony compatibility header
// Provides declarations for pthread functions not available on OpenHarmony (musl-based)
// This header must be force-included before any Boost headers

#ifndef OHOS_COMPAT_H
#define OHOS_COMPAT_H

#ifdef __OHOS__
#include <pthread.h>

// pthread_setcancelstate is not implemented on OpenHarmony
// Provide a stub declaration so Boost inline code can compile
extern "C" int pthread_setcancelstate(int state, int *oldstate);

#endif // __OHOS__

#endif // OHOS_COMPAT_H
"""

OHOS_COMPAT_CPP = """// OpenHarmony compatibility stub for pthread_setcancelstate
// OpenHarmony (musl-based) does not implement pthread cancellation functions
// This stub provides the runtime implementation; declaration is in ohos_compat.h

#ifdef __OHOS__
#include <pthread.h>

extern "C" int pthread_setcancelstate(int state, int *oldstate)
{
    // Stub: OpenHarmony does not support pthread cancellation
    // Always return success (0) and set oldstate to PTHREAD_CANCEL_ENABLE
    (void)state; // suppress unused parameter warning
    if (oldstate)
    {
        *oldstate = PTHREAD_CANCEL_ENABLE;
    }
    return 0;
}
#endif
"""


class SnapcastConan(ConanFile):
    name = "snapcast"
    version = "0.35.0"
    description = "Multiroom client-server audio player (snapserver + snapclient)"
    license = "GPLv3+"
    homepage = "https://github.com/snapcast/snapcast"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("alsa-lib/1.2.16.1")
        self.requires("boost/1.84.0")
        self.requires("flac/1.4.3")
        self.requires("libvorbis/1.3.7")
        self.requires("opus/1.5.2.1")
        self.requires("libsoxr/0.1.3")
        self.requires("openssl/1.1.1w")
        self.requires("expat/2.8.2.1.1")
        # Override libogg to resolve flac(1.3.5)/libvorbis(1.3.6) version conflict
        self.requires("libogg/1.3.6", override=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS platform: disable features not available in the registry
        tc.variables["BUILD_WITH_AVAHI"] = False      # avahi-client not in registry
        tc.variables["BUILD_WITH_TREMOR"] = False       # tremor not in registry, use libvorbis
        tc.variables["BUILD_WITH_ALSA"] = True
        tc.variables["BUILD_WITH_FLAC"] = True
        tc.variables["BUILD_WITH_VORBIS"] = True
        tc.variables["BUILD_WITH_OPUS"] = True
        tc.variables["BUILD_WITH_EXPAT"] = True
        tc.variables["BUILD_WITH_SSL"] = True
        tc.variables["BUILD_WITH_PULSE"] = False       # PulseAudio not available
        tc.variables["BUILD_WITH_JACK"] = False         # JACK not available
        tc.variables["BUILD_WITH_PIPEWIRE"] = False     # PipeWire not available
        tc.variables["BUILD_WITH_SDL2"] = False         # SDL2 not available
        tc.variables["BUILD_TESTS"] = False
        tc.variables["WERROR"] = False
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["BUILD_STATIC_LIBS"] = True
        tc.generate()

        # Fix: pkg_search_module sets ALSA_LIBRARIES without -L path
        # Add all dependency lib dirs to LIBRARY_PATH so linker can find -lasound etc.
        env = Environment()
        for dep in self.dependencies.values():
            cpp_info = getattr(dep, "cpp_info", None)
            if cpp_info:
                for d in cpp_info.libdirs:
                    env.append_path("LIBRARY_PATH", d)
        env.vars(self).save_script("snapcast_library_path")

    def build(self):
        apply_conandata_patches(self)
        # Create ohos_compat files (not patches since they're new files)
        save(self, os.path.join(self.source_folder, "common", "ohos_compat.h"), OHOS_COMPAT_H)
        save(self, os.path.join(self.source_folder, "common", "ohos_compat.cpp"), OHOS_COMPAT_CPP)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
