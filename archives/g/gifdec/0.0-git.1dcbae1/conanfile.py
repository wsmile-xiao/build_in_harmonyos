#!/usr/bin/env python3
"""Conan recipe for gifdec 0.0-git.1dcbae1.

gifdec is a minimalist C GIF decoder (public domain, bylecram).
Upstream ships NO build system at all (no CMakeLists.txt / Makefile —
only gifdec.c + gifdec.h, an SDL2-based example player and a README).
This recipe:

  * generates a minimal CMakeLists.txt (upstream has none) that compiles
    the unmodified upstream gifdec.c into a thin static library,
  * installs gifdec.h + libgifdec.a,
  * runs NO upstream tests in build() (upstream ships no test suite:
    example.c is an interactive SDL2 player, not a test — see
    test_package/MANIFEST.yml); consumer-side verification happens in
    test_package with programmatically synthesized GIF byte streams.

Upstream snapshot: master @ 1dcbae19363597314f6623010cc80abad4e47f7c
(the 7-hex prefix 1dcbae1 is the version tag per the master-only
repository versioning rule 0.0-git.{hash7}).

gifdec.c is plain C99 using POSIX fd I/O (open/read/lseek/close) plus
mem*() — zero third-party dependencies, no libm, no patches needed on
OHOS aarch64 (musl) with clang 15.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, save

CMAKELISTS = """\
cmake_minimum_required(VERSION 3.15)
project(gifdec C)
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Thin static library from the single upstream TU (gifdec.c is a plain
# .c file, NOT a header/source hybrid — no implementation macro needed)
add_library(gifdec gifdec.c)
target_include_directories(gifdec PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

install(TARGETS gifdec
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib)
install(FILES gifdec.h DESTINATION include)
"""


class GifdecConan(ConanFile):
    name = "gifdec"
    version = "0.0-git.1dcbae1"
    description = "Minimalist C library for reading GIF files (public domain)"
    license = "Unlicense"  # upstream README: public domain
    homepage = "https://github.com/lecram/gifdec"
    url = "https://github.com/lecram/gifdec"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2/kpeople5 precedent).
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # R26: static by default — no system-name .so collision risk
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # upstream code is plain C99 (README: "less than 500 lines of C99")
        tc.variables["CMAKE_C_STANDARD"] = "99"
        tc.variables["CMAKE_C_STANDARD_REQUIRED"] = "ON"
        tc.generate()

    def build(self):
        # upstream ships no build system: generate a thin CMakeLists.txt
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), CMAKELISTS)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # No upstream test suite exists (example.c is an SDL2 player demo,
        # not a test). Consumer verification runs in test_package with
        # synthesized GIF byte streams — declared in test_package/MANIFEST.yml.

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["gifdec"]
        # gifdec.c uses only open/read/lseek/close + mem*() from libc —
        # no libm, no other system libs on musl/OHOS
