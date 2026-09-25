#!/usr/bin/env python3
"""Conan recipe — isospec 2.3.2 (IsoSpec++ isotopic distribution library).

Upstream: https://github.com/MatteoLacki/IsoSpec (C++17, CMake).

OHOS adaptations (no source patches needed):
  - The top-level CMake project also configures man/ whose install() rules
    reference doxygen/rsvg build artifacts that never exist in a plain
    library build (`install(DIRECTORY .../html ...)`).  We therefore build
    only the two library targets (`IsoSpec++-shared`, `IsoSpec++-static`)
    and copy headers + libraries in package() instead of running a global
    `cmake --install`, which would abort on the missing doc directories.
  - Shared objects linked on OHOS get `-Wl,-z,max-page-size=16384`:
    HarmonyOS aarch64 loaders require 16 KiB-aligned LOAD segments for
    dlopen()-able libraries (4 KiB-aligned objects built by the NDK clang
    are rejected at load time with a misleading "Permission denied").
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class IsoSpecConan(ConanFile):
    name = "isospec"
    version = "2.3.2"
    description = "IsoSpec++ — fast analytical computation of isotopic distributions of molecules"
    license = "BSD-2-Clause"
    homepage = "https://github.com/MatteoLacki/IsoSpec"
    url = "https://github.com/MatteoLacki/IsoSpec"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        pass  # no patches: sources are fetched from conandata.yml

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass  # no third-party dependencies: boost's binomial sampler is
        # vendored in src/IsoSpec++/btrd.h (Boost Software License 1.0)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        if self.settings.os == "OHOS":
            linker_flags = "-Wl,-z,max-page-size=16384"
            tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = linker_flags
            tc.variables["CMAKE_MODULE_LINKER_FLAGS"] = linker_flags
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = linker_flags
        tc.generate()

    def build(self):
        apply_conandata_patches(self)  # no-op: conandata.yml declares no patches
        cmake = CMake(self)
        cmake.configure()
        # Build only the library targets; the global `install` target would
        # also run man/'s install() rules which need doxygen/rsvg artifacts.
        if self.options.shared:
            cmake.build(target="IsoSpec++-shared")
        else:
            cmake.build(target="IsoSpec++-static")

    def package(self):
        src_inc = os.path.join(self.source_folder, "src", "IsoSpec++")
        # Mirrors upstream install(DIRECTORY ... FILES_MATCHING *.h *.hpp):
        # headers end up in include/IsoSpec++/ so consumers
        # `#include <IsoSpec++/isoSpec++.h>`.
        copy(self, "*.h", src_inc, os.path.join(self.package_folder, "include", "IsoSpec++"))
        copy(self, "*.hpp", src_inc, os.path.join(self.package_folder, "include", "IsoSpec++"))
        libdir = os.path.join(self.build_folder, "src", "IsoSpec++")
        if self.options.shared:
            # OHOS note: CMake's Platform/HarmonyOS module does not produce
            # a SONAME/symlink chain — the build tree contains a single
            # real file `libIsoSpec++.so` (no .so.2 / .so.2.3.2), and
            # consumers link/resolve it by name, which is self-consistent.
            copy(self, "libIsoSpec++.so*", libdir, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libIsoSpec++.a", libdir, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["IsoSpec++"]
