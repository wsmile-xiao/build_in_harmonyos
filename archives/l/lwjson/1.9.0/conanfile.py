#!/usr/bin/env python3
"""Conan recipe for lwjson 1.9.0 — Lightweight JSON parser/serializer for C.

lwjson is a CMake-built static library (two targets: `lwjson` core and
`lwjson_debug` debug module) with public headers under lwjson/src/include/.
Upstream ships NO install() rules, so a minimal CMake patch
(patches/0001-cmake-install-rules.patch) adds them:

  - install(TARGETS lwjson lwjson_debug ...)  -> lib/
  - install(DIRECTORY src/include/ ...)       -> include/ (lwjson/*.h)
  - install(FILES <build>/lib_inc/lwjson_opts.h ...) — the generated
    configuration header (COPYONLY from lwjson_opts_template.h); needed
    because lwjson/lwjson_opt.h does `#include "lwjson_opts.h"`.

Notes:
  - R32: settings.os gate accepts both Linux and OHOS.
  - R33: compiler/flags come from CMakeToolchain, no bare shell variables.
  - L1/upstream tests: top-level CMake registers ctest entry `Test` (tests/
    subdir); build() runs it as the upstream check. The other five upstream
    test entries (test_json_data_types / test_json_find /
    test_json_parse_basic / test_parse_token_count / test_serializer) are
    per-entry CMake variants driven by upstream tests/test.py — they were
    run during adaptation (see notes.md ledger); the recipe keeps the
    default registered entry to stay CI-deterministic.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class LwjsonConan(ConanFile):
    name = "lwjson"
    version = "1.9.0"
    description = "lwjson - Lightweight JSON parser and serializer library written in C (MaJerle)"
    license = "MIT"
    homepage = "https://github.com/MaJerle/lwjson"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: platform gate must accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lwjson is supported only on Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # L1: upstream registered ctest entry (tests/CTestTestfile.cmake)
        # Note: the top-level build dir has no CTestTestfile.cmake; the
        # upstream add_test lives in the tests/ subdirectory.
        ctest_dir = os.path.join(self.build_folder, "tests")
        if os.path.isdir(ctest_dir):
            self.run("ctest --test-dir {} --output-on-failure".format(ctest_dir),
                     env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["lwjson_debug", "lwjson"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "lwjson")
        self.cpp_info.set_property("cmake_target_name", "lwjson::lwjson")
        self.cpp_info.set_property("cmake_target_aliases", ["lwjson::lwjson_debug"])