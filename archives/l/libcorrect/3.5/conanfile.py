#!/usr/bin/env python3
"""Conan recipe for libcorrect 3.5 — C library for Convolutional codes and Reed-Solomon.

libcorrect upstream is a CMake project (cmake_minimum_required(VERSION 3.5), no git
tags/releases on GitHub; this "3.5" maps to upstream master HEAD ee82e667, official
codeload commit archive):
  - `make`            → libcorrect.so + libcorrect.a (correct / correct_static targets)
  - `make test_runners` → builds the upstream test executables under build/tests
  - `ctest`           → runs the 4 unconditionally-registered upstream tests

Build notes:
  - The recipe uses CMake (libcorrect's own build system), not autotools.
  - OHOS/aarch64: HAVE_SSE stays off (x86intrin check fails without SSE), so the
    convolutional-sse test is not instantiated; HAVE_LIBFEC stays off (optional
    Phil Karn libfec interop, not published in ohpcd registry) so the fec-interop
    tests are not instantiated. Both are upstream-conditional branches.
  - E074 (SELinux jobserver FIFO): build with -j1.
  - R34: test_package actually encodes + decodes a Reed-Solomon block via the
    public API (correct_reed_solomon_*), printing the observable result.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibcorrectConan(ConanFile):
    name = "libcorrect"
    version = "3.5"
    description = "libcorrect - C library for Convolutional codes and Reed-Solomon error correction"
    license = "BSD-3-Clause"
    homepage = "https://github.com/quiet/libcorrect"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: platform gate must accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libcorrect is supported only on Linux/OHOS, not " + str(self.settings.os))

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Build both the shared (correct) and static (correct_static) targets.
        # E074: -j1 (HarmonyOS SELinux forbids the make jobserver FIFO).
        cmake = CMake(self)
        cmake.configure(variables={"BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF"})
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["correct"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.system_libs = ["m"]