#!/usr/bin/env python3
"""Conan recipe — tweeny 4.1.0 (CMake, header-only).

Tweeny is a header-only C++17 inbetweening library (30+ easing functions,
multi-point tweening, forward/backward stepping, timeline seeking). Upstream
ships an INTERFACE CMake target plus install/export rules
(TweenyConfig.cmake / tweeny::tweeny), so this recipe drives the real CMake
install instead of copying headers by hand.

Platform notes:
  * Upstream declares `cmake_minimum_required(VERSION 3.23...3.28)`; local and
    CI CMake are 4.x, which accept a minimum >= 3.5 — no
    CMAKE_POLICY_VERSION_MINIMUM injection is needed (unlike the v3 tag whose
    3.0 minimum required the E103 workaround).
  * Documentation/single-header builds are disabled: they pull doxygen/uv
    tooling that is not part of this package. Tests are disabled in the recipe
    build (they need Catch2 v3, resolved only in the adaptation flow).

Version slug: 4.1.0 is a valid Conan version — no set_version() needed.

Upstream v4.1.0 ships a Catch2 test suite (135 TEST_CASE in src/tests/); those
are enumerated and executed in the adaptation flow (135/135 passed), and the
package-level verification is delivered by the test_package consumer test,
which compiles the installed headers against the OHOS clang and asserts on
interpolation behaviour.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class TweenyConan(ConanFile):
    name = "tweeny"
    version = "4.1.0"
    description = "A modern C++ animation/tweening library (header-only, 30+ easings)."
    license = "MIT"
    homepage = "https://github.com/mobius3/tweeny"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TWEENY_BUILD_DOCUMENTATION"] = False
        tc.variables["TWEENY_BUILD_SINGLE_HEADER"] = False
        tc.variables["TWEENY_BUILD_TESTS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # NOTE: dst must be absolute — a relative dst is not resolved against
        # the package folder by conan.tools.files.copy (it lands in the
        # process cwd), so the template's `dst="licenses"` silently drops it.
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        # Upstream installs headers under include/tweeny and exports the
        # INTERFACE target via lib/cmake/Tweeny (TweenyConfig.cmake,
        # NAMESPACE tweeny::). The installed include root is `include`
        # (mirrors upstream's $<INSTALL_INTERFACE:include>), so consumers
        # #include <tweeny/tweeny.h> / <tweeny/easing.h>.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "Tweeny")
        self.cpp_info.set_property("cmake_target_name", "tweeny::tweeny")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
