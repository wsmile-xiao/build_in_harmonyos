#!/usr/bin/env python3
"""Conan recipe — eathread 0.0.0-f3c6c54 (EAThread, Electronic Arts).

EAThread is the EA cross-platform threading library: thread, mutex,
semaphore, condition, barrier, RW-lock, spin-lock, futex, callstack and
storage primitives over POSIX/C++11 backends. Built with CMake.

OHOS adaptation:
  - Upstream CMakeLists.txt fetches EABase via FetchContent; patched to use
    the published conan `eabase` package instead (no network at build time).
  - Upstream has no install rules; patch adds install(TARGETS EAThread) and
    header installation so the package is consumable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class EathreadConan(ConanFile):
    name = "eathread"
    version = "0.0.0-f3c6c54"
    description = "EAThread - Electronic Arts cross-platform threading library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/electronicarts/EAThread"
    url = "https://github.com/electronicarts/EAThread"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("eabase/0699a15")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Tests are built/run as part of the adaptation verification, not in
        # the conan package build (their EATest framework is not published).
        tc.variables["EATHREAD_BUILD_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # eathread public headers include <EABase/eabase.h>; consumers must
        # receive eabase's include dirs transitively.
        self.cpp_info.libs = ["EAThread"]
