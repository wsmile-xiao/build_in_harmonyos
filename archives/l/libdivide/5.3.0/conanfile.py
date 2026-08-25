#!/usr/bin/env python3
"""Conan recipe — libdivide 5.3.0

libdivide is a header-only C/C++ library for optimizing integer division.
It replaces expensive integer divide instructions with cheaper multiply
and shift sequences at runtime.

The package itself is header-only (package_type=header-library), so no
.so/.a is produced. However, per the PR requirement that upstream tests
must actually be executed (not merely declared), this recipe builds and
runs the upstream correctness tests in build() before packaging the
header.

Upstream tests (test/ directory):
  - tester    (test/tester.cpp)    — C++ scalar + vector correctness
  - test_c99  (test/test_c99.c)    — C99 scalar correctness

The tests are compiled directly with the profile's CC/CXX (not via the
upstream CMake) to avoid check_cxx_source_runs cross-compilation issues
with x86 SIMD detection. The upstream CMake uses try_run for SSE/AVX
which cannot execute under cross-compilation; direct compilation with
the conan-provided toolchain is the correct, portable approach.

SIMD note for OpenHarmony aarch64:
  - NEON is auto-detected by the libdivide.h header itself at compile
    time via __ARM_NEON / __aarch64__ — no CMake detection needed.
  - SSE2/AVX2/AVX512 are x86-only and simply not compiled on aarch64.
  - tester output "SIMD ISAs: none" = scalar + NEON path (if enabled).
"""
import os
import shlex

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class LibdivideConan(ConanFile):
    name = "libdivide"
    version = "5.3.0"
    description = "Header-only C/C++ library for optimizing integer division"
    license = "BSL-1.0 OR Zlib"
    homepage = "https://github.com/ridiculousfish/libdivide"
    url = ""

    package_type = "header-library"

    # R32: settings.os check must include both Linux and OHOS
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only package: the library itself needs no compilation.
        # Build and run upstream correctness tests per PR requirement.
        #
        # Tests are compiled directly with the profile's CC/CXX rather
        # than via the upstream CMake. The upstream CMakeLists.txt uses
        # check_cxx_source_runs() for SSE2/AVX2/AVX512 detection, which
        # tries to *execute* compiled test binaries — this fails under
        # cross-compilation. Direct compilation sidesteps this entirely;
        # libdivide.h auto-detects NEON via __ARM_NEON at preprocess time.
        src = self.source_folder
        inc = "-I{} -I{}/test".format(src, src)

        # C++ correctness test: tester.cpp
        cxx = os.environ.get("CXX", "clang++")
        cxxflags = os.environ.get("CXXFLAGS", "")
        self.run(
            "{} -std=c++11 -O2 {} {} -pthread {}/test/tester.cpp -o tester".format(
                shlex.quote(cxx), cxxflags, inc, src),
            env="conanbuild")

        # C99 correctness test: test_c99.c
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "")
        self.run(
            "{} -std=c99 -O2 {} {} {}/test/test_c99.c -o test_c99".format(
                shlex.quote(cc), cflags, inc, src),
            env="conanbuild")

        # Run both upstream correctness tests.
        # tester    — C++ scalar + vector correctness
        # test_c99  — C99 scalar correctness
        self.run("./tester", env="conanrun")
        self.run("./test_c99", env="conanrun")

    def package(self):
        # Copy the single header into include/
        copy(self, "libdivide.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        # Copy license
        copy(self, "LICENSE.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libdivide")
        self.cpp_info.set_property("cmake_target_name", "libdivide::libdivide")
        # Header-only: no libs to link
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
