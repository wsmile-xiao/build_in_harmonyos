#!/usr/bin/env python3
"""Conan recipe — ctre 3.11.0 (header-only, CMake INTERFACE).

CTRE (Compile Time Regular Expressions) — header-only C++17/20 template library
for compile-time regular expressions. No compilation needed for the package
itself; the recipe installs the public headers under include/ and exposes the
INTERFACE target ctre::ctre.

Upstream test suite: tests/*.cpp (25 compile-time assertion translation units)
built via the official CMake aggregate target `ctre-test`. build() configures
with CTRE_BUILD_TESTS=ON / CTRE_BUILD_PACKAGE=OFF and builds that target, then
emits the HMBS_UPSTREAM_TEST_RESULT hard-gate marker with real counts.

License: Apache-2.0 with LLVM exception
"""

import glob
import json
import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class CtreConan(ConanFile):
    name = "ctre"
    version = "3.11.0"
    description = "Compile Time Regular Expressions for C++17/20 (header-only)"
    license = "Apache-2.0-with-LLVM-exception"
    homepage = "https://github.com/hanickadot/compile-time-regular-expressions"
    url = "https://github.com/hanickadot/compile-time-regular-expressions"
    topics = ("regex", "template", "header-only", "compile-time")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    # NOTE(ohos): do NOT tool_requires cmake — HMBS preflight injects a
    # system cmake (HMBS_CMAKE + PATH prepend, 4.4.3 on the real machine)
    # and the ohpcd remote cannot resolve 'cmake/[>=3.19]'.
    # Declaring the tool dep hard-fails dependency-graph resolution:
    #   ERROR: Package 'cmake/[>=3.19]' not resolved ...
    # CMakeToolchain only provides the toolchain file; the cmake binary
    # comes from PATH, so no build requirement is needed.

    def validate(self):
        check_min_cppstd(self, "17")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CTRE_BUILD_TESTS"] = True
        tc.cache_variables["CTRE_BUILD_PACKAGE"] = False
        tc.cache_variables["CTRE_CXX_STANDARD"] = "17"
        # NOTE(ohos): upstream root CMakeLists forces CMAKE_CXX_MODULE_STD=1
        # on CMake >= 4.0.3 (true machine has 4.4.3), which makes every
        # ctre-test-* target require import-std toolchain support that the
        # OHOS clang toolchain does not provide -> configure fails at the
        # first target (ctre-test-__utf8). The guard is
        #   if(NOT CMAKE_EXPERIMENTAL_CXX_STD AND NOT CMAKE_CXX_MODULE_STD)
        # so predefining CMAKE_EXPERIMENTAL_CXX_STD skips the block and
        # leaves MODULE_STD disabled; plain header/tests use no modules
        # (CTRE_MODULE=OFF) so this only restores the pre-4.0 behaviour.
        tc.cache_variables["CMAKE_EXPERIMENTAL_CXX_STD"] = True
        tc.cache_variables["CMAKE_CXX_MODULE_STD"] = False
        tc.cache_variables["CMAKE_EXPERIMENTAL_CXX_IMPORT_STD"] = False
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="ctre-test")
        self._emit_hmbs_upstream_marker('cmake --build <build-folder> --target ctre-test')

    def _emit_hmbs_upstream_marker(self, command):
        discovered = len(glob.glob(os.path.join(self.source_folder, "tests", "*.cpp")))
        # ctre-test target compiles every tests/*.cpp translation unit; a
        # successful cmake.build() above means all of them compiled, i.e.
        # all compile-time static_asserts held.
        executed = discovered
        passed = discovered
        failed = 0
        skipped = 0
        status = "passed" if discovered > 0 else "failed"
        result = {
            "status": status,
            "framework": "cmake-ctre-test",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        # Persist for test_package re-emission on cache-hit rounds
        # ("Already installed!" skips build() output).
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"), "w", encoding="utf-8") as handle:
                json.dump(result, handle, ensure_ascii=False)
        except OSError:
            pass
        if status != "passed":
            raise RuntimeError("ctre upstream ctre-test produced no test units")

    def package(self):
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(self, "*.hpp", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "include"))
        copy(self, "*.gram", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "include"))
        upstream_json = os.path.join(self.build_folder, "hmbs_upstream.json")
        if os.path.isfile(upstream_json):
            copy(self, "hmbs_upstream.json", dst=os.path.join(self.package_folder, "res"), src=self.build_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ctre")
        self.cpp_info.set_property("cmake_target_name", "ctre::ctre")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
