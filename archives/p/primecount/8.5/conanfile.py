#!/usr/bin/env python3
"""Conan recipe for primecount 8.5 (CMake build system).

Build system: CMake
Dependencies: none — libprimesieve is vendored under lib/primesieve and
              built from source (BUILD_LIBPRIMESIEVE=ON, the upstream default).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PrimecountConan(ConanFile):
    name = "primecount"
    version = "8.5"
    description = "primecount is a C/C++ library for counting the number of primes <= x"
    license = "BSD-2-Clause"
    homepage = "https://github.com/kimwalisch/primecount"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Static libprimecount (upstream default); avoids .so pollution.
        tc.variables["BUILD_SHARED_LIBS"] = False
        # Don't build the upstream test suite (L1 test is test_package).
        tc.variables["BUILD_TESTS"] = False
        # OpenMP off: OHOS may not ship libomp; primecount falls back to
        # its sequential implementation (fully functional).
        tc.variables["WITH_OPENMP"] = False
        # Multiarch off: disables runtime SVE/AVX512 CPU dispatch, avoiding
        # extra instruction-set build flags; base aarch64 code is used.
        tc.variables["WITH_MULTIARCH"] = False
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
        # libprimecount.a has a PRIVATE dependency on the vendored
        # libprimesieve.a (primesieve::iterator, primesieve::set_num_threads,
        # ...); both static archives are installed into lib/. A static archive
        # does not resolve its own private cross-references, so consumers must
        # link BOTH archives. Order matters: primecount before primesieve so the
        # linker resolves primecount's undefined primesieve symbols.
        self.cpp_info.libs = ["primecount", "primesieve"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]  # installs the primecount CLI binary
        # C++ standard library needed when linking the static libs.
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["c++"]
