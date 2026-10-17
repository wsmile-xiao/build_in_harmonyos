#!/usr/bin/env python3
"""Conan recipe for itsy_bitsy 0.8 (itsy.bitsy header-only C++ library, CMake)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ItsyBitsyConan(ConanFile):
    name = "itsy_bitsy"
    version = "0.8"
    description = "Standard bit utilities to supplement the C and C++ standard libraries"
    license = "BSL-1.0"
    homepage = "https://github.com/ThePhD/itsy_bitsy"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("bits", "bitset", "header-only", "c++17")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # itsy/detail/span.hpp emits "#error a span of some sort is required"
        # unless <nonstd/span.hpp> is on the include path, so bit_span.hpp
        # cannot be consumed without span-lite.  This is a public dependency,
        # unlike range-v3, which is only used by the upstream test suite.
        self.requires("span-lite/0.11.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The v0.8 source archive contains empty git-submodule directories.
        # range-v3 is test-only; span-lite is also staged here because the
        # upstream tests include it through the original vendor path.
        for key, destination in (
            ("range_v3", os.path.join(self.source_folder, "vendor", "range-v3")),
            ("span_lite", os.path.join(self.source_folder, "vendor", "span-lite")),
        ):
            get(
                self,
                **self.conan_data["test_sources"][key],
                strip_root=True,
                destination=destination,
            )

    def generate(self):
        # Pin the text encoding of every Python process started by the build.
        # Upstream's single-header generator (single/single.py:138) reads a git
        # version probe with os.popen(), and that pipe is decoded with the
        # interpreter's *host-derived* preferred encoding.  On the CI worker it
        # resolved to a str-buffered codec, so generating the single header died
        # with:
        #     File "<frozen codecs>", line 321, in decode
        #     TypeError: can't concat str to bytes
        # and make aborted at 1%.  UTF-8 mode makes getpreferredencoding()
        # deterministic (verified on device: it reports 'utf-8' even under a
        # hostile LC_ALL/PYTHONIOENCODING), so the generated header no longer
        # depends on the build machine's locale.
        pyenv = Environment()
        pyenv.define("PYTHONUTF8", "1")
        pyenv.define("PYTHONIOENCODING", "utf-8")
        pyenv.vars(self, scope="build").save_script("python-utf8-build")

        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            # CMake 4.1 has no built-in HarmonyOS platform module.  The OHOS
            # clang toolchain remains in use; Linux selects the compatible
            # libc++/POSIX CMake path without changing the target compiler.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "17"
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.cache_variables["ITSY_BITSY_SINGLE"] = "ON"
        tc.cache_variables["ITSY_BITSY_TESTS"] = "ON"
        tc.cache_variables["ITSY_BITSY_EXAMPLES"] = "ON"
        tc.cache_variables["ITSY_BITSY_BENCHMARKS"] = "OFF"
        # Report the failing CTest entry's own output, not just the summary
        # count, so the conan create log is usable as test evidence.  Two
        # Conan-specific facts behind this form:
        #   * a Python list/tuple here is serialised as its repr
        #     ("['--output-on-failure']") into the generated "make test" rule
        #     and breaks ctest, so it must be a plain string (E301 family);
        #   * CMake.ctest() is avoided because it injects
        #     "--parallel <tools.build:jobs>" (20 on this device), while the
        #     build-system "test" target keeps the suite serial.
        tc.cache_variables["CMAKE_CTEST_ARGUMENTS"] = "--output-on-failure"
        # OHOS libc++ marks allocator::construct deprecated in C++17, and an
        # upstream allocator test increments an otherwise unused index.  The
        # upstream test targets append -Wall -Wextra -Werror after this cache
        # value, so demote only that diagnosed warning and suppress the
        # libc++ compatibility warning; no assertions or test sources change.
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_CXX_FLAGS"] = (
                "-Wno-deprecated-declarations "
                "-Wno-error=unused-but-set-variable"
            )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "2"], build_tool_args=["-j2"])
        # The formal upstream tests/ suite has 6 CTest entries: 2 runtime
        # drivers, 2 compile-time executables, and 2 expected-failure checks.
        # ITSY_BITSY_EXAMPLES=ON adds 14 separate example checks, so the
        # complete configured CTest run reports 20 entries.
        cmake.test(build_tool_args=["-j2"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.requires = ["span-lite::span-lite"]
        self.cpp_info.set_property("cmake_file_name", "itsy.bitsy")
        self.cpp_info.set_property("cmake_target_name", "itsy::bitsy")
        self.cpp_info.set_property("pkg_config_name", "itsy.bitsy")
