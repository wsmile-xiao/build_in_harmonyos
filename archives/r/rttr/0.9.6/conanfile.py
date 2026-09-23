#!/usr/bin/env python3
"""Conan recipe — rttr 0.9.6 (CMake).

rttr — Run Time Type Reflection (https://www.rttr.org), a C++11 reflection
library (MIT, Axel Menzel). Upstream builds with CMake and exports the
RTTR::Core target (librttr_core.so / librttr_core.a). No third-party
dependencies: the bundled Catch 1.12 (unit tests), RapidJSON and Nonius
(benchmarks) are internal-only, and Boost is required by BUILD_BENCHMARKS
only — kept OFF here.

Native exploration evidence (device, this task, notes.md / reports/):
  - upstream Catch unit suite on the device (aarch64 OHOS, clang 15):
    531/531 executed test cases and 4891/4891 assertions passed against the
    shared library; the 15 remaining upstream TEST_CASEs live in
    variant_array_view_test.cpp, which upstream's unit_tests.cmake excludes
    because the tested variant_array_view API does not exist in 0.9.6
    (single-file compile probe fails with "unknown type name
    'variant_array_view'").
  - porting patches (24 files): clang 15 -Werror fixes in library headers
    (implicit int-to-float narrowing in number_conversion.h, ordered
    function-pointer comparison in compare_less_impl.h /
    misc_type_traits.h), aarch64 missing from RTTR_ARCH_TYPE, and
    unit-test-only fixes (C++17 std::variant ambiguity, missing virtual
    destructors in fixtures, deprecated builtin, intentional self-assign).

Build notes:
  - os=OHOS maps to CMAKE_SYSTEM_NAME=HarmonyOS, which stock CMake does not
    know (no Platform/HarmonyOS), so UNIX stays undefined and upstream
    config.cmake aborts with "Could not set install folders for this
    platform!". Pin CMAKE_SYSTEM_NAME=Linux, same doctrine as the other
    CMake recipes in this repo.
  - upstream cmake_minimum_required is 3.0, rejected by CMake >= 4; pass
    CMAKE_POLICY_VERSION_MINIMUM=3.5 instead of patching the source.
  - install rules are gated behind BUILD_INSTALLER (with it OFF,
    `cmake install` deploys nothing), so it stays ON; the CPack-based
    BUILD_PACKAGE stays OFF.
  - upstream's exported config installs lowercase share/rttr/cmake/
    rttr-config.cmake (target RTTR::Core, INTERFACE_COMPILE_DEFINITIONS
    RTTR_DLL for shared). Removed from the package: CMakeDeps regenerates
    RTTRConfig.cmake and the lowercase file could shadow it.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class RttrConan(ConanFile):
    name = "rttr"
    version = "0.9.6"
    description = ("Run Time Type Reflection for C++ — access types, methods and "
                   "properties at runtime (no third-party dependencies)")
    license = "MIT"
    homepage = "https://www.rttr.org"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/r/rttr/0.9.6"
    topics = ("reflection", "rtti", "metadata", "cpp11")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.options.shared:
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is validated for Linux/OHOS, not {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["BUILD_RTTR_DYNAMIC"] = bool(self.options.shared)
        tc.cache_variables["BUILD_STATIC"] = not self.options.shared
        # Library-only package; upstream bundles tests, benchmarks, examples,
        # doxygen documentation and a CPack config — all off. Keep the
        # upstream test sources out of the packaged build (they are exercised
        # in the native exploration phase, see MANIFEST.yml).
        tc.cache_variables["BUILD_UNIT_TESTS"] = "OFF"
        tc.cache_variables["BUILD_BENCHMARKS"] = "OFF"
        tc.cache_variables["BUILD_EXAMPLES"] = "OFF"
        tc.cache_variables["BUILD_DOCUMENTATION"] = "OFF"
        tc.cache_variables["BUILD_INSTALLER"] = "ON"
        tc.cache_variables["BUILD_PACKAGE"] = "OFF"
        # Deterministic single-TU-set builds across devices/CI workers; the
        # native exploration run used the same flag.
        tc.cache_variables["USE_PCH"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        shutil.rmtree(os.path.join(self.package_folder, "share", "rttr", "cmake"),
                      ignore_errors=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "RTTR")
        self.cpp_info.set_property("cmake_target_name", "RTTR::Core")
        self.cpp_info.libs = ["rttr_core"]
        if self.options.shared:
            # Matches upstream's exported INTERFACE_COMPILE_DEFINITIONS for
            # the shared build; static consumers need no define (RTTR_API
            # stays empty without RTTR_DLL).
            self.cpp_info.defines = ["RTTR_DLL"]
