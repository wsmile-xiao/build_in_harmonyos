#!/usr/bin/env python3
"""Conan recipe for tidy 5.8.0 — tidy-html5 HTML checker/fixer.

W3C tidy reborn as tidy-html5 (htacg).  CMake build, zero external
dependencies.  The static libtidy.a is always built and the `tidy`
console links it statically by default (TIDY_CONSOLE_SHARED=OFF) —
which also sidesteps this platform's shared-library loader quirks.

Platform notes:
- Upstream regression suite is driven by Ruby (regression_testing/
  Gemfile + test.rb); Ruby does not exist on this platform, so upstream
  tests are declared non-executable (MANIFEST.yml).  Verification is
  carried by the consumer test_package.
- Nothing is stripped on install (llvm-strip output is refused by the
  platform's exec policy — yices 2.7.0 evidence + knowledge draft).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class TidyConan(ConanFile):
    name = "tidy"
    version = "5.8.0"
    description = ("tidy-html5 - fixes and cleans up HTML, XML and XHTML, "
                   "and diagnoses markup errors")
    license = "W3C-19980720"
    homepage = "https://github.com/htacg/tidy-html5"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]) — conan's
        # get() handles both shapes natively.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIB"] = bool(self.options.shared)
        tc.variables["TIDY_CONSOLE_SHARED"] = False
        tc.variables["BUILD_TAB2SPACE"] = False
        tc.variables["BUILD_SAMPLE_CODE"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=os.path.join(self.source_folder,
                                                   "README"),
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Tidy")
        self.cpp_info.set_property("cmake_target_name", "Tidy::Tidy")
        self.cpp_info.libs = ["tidy"]
