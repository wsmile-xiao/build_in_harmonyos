#!/usr/bin/env python3
"""Conan recipe for libassert-cpp/1.2.1 (CMake library).

libassert is a C++ assertion library (header + src/assert.cpp) that ships a
CMake `assert` target. The consumer-facing header installs under
`${CMAKE_INSTALL_INCLUDEDIR}/assert/assert/assert.hpp` and is used with
`#include <assert.hpp>`.

Upstream 1.2.1 fetches cpptrace v0.2.1 via FetchContent unless
ASSERT_USE_EXTERNAL_CPPTRACE=ON. This recipe vendors the cpptrace release
tarball in `conandata.yml` and points FetchContent at the local source dir,
so a clean build never needs the github.com git protocol (unreachable on
OHOS CI workers).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibassertCppConan(ConanFile):
    name = "libassert-cpp"
    version = "1.2.1"
    description = "The most over-engineered C++ assertion library"
    license = "MIT"
    homepage = "https://github.com/jeremy-rifkin/libassert"
    url = "https://github.com/jeremy-rifkin/libassert"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source_data = dict(self.conan_data["sources"][str(self.version)])
        get(self, **source_data, strip_root=True, filename="libassert-1.2.1.tar.gz")
        # Vendor cpptrace for FetchContent so the clean build does not run a
        # github.com git clone (network protocol unreachable on OHOS).
        cpptrace_data = dict(self.conan_data["cpptrace"])
        get(
            self,
            **cpptrace_data,
            strip_root=True,
            filename="cpptrace-0.2.1.tar.gz",
            destination=os.path.join(self.source_folder, "_deps", "cpptrace-src"),
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["ASSERT_BUILD_TESTS"] = "OFF"
        tc.variables["ASSERT_BUILD_BASIC_TEST"] = "OFF"
        tc.variables["ASSERT_USE_MAGIC_ENUM"] = "ON"
        # Point FetchContent at the vendored local cpptrace source instead of
        # git-cloning github.com (unreachable on OHOS CI workers).
        tc.variables["ASSERT_USE_EXTERNAL_CPPTRACE"] = "OFF"
        tc.variables["FETCHCONTENT_SOURCE_DIR_CPPTRACE"] = os.path.join(
            self.source_folder, "_deps", "cpptrace-src"
        )
        # cpptrace auto-config misdetects the unknown OHOS platform as
        # Windows and selects the dbghelp back-end, which needs <windows.h>
        # and fails. Pin the back-ends available in the OHOS sysroot
        # (execinfo.h + libunwind for unwinding, cxxabi for demangling,
        # no symbol provider) so its auto-config block is skipped.
        tc.variables["CPPTRACE_UNWIND_WITH_EXECINFO"] = "ON"
        tc.variables["CPPTRACE_GET_SYMBOLS_WITH_NOTHING"] = "ON"
        tc.variables["CPPTRACE_DEMANGLE_WITH_CXXABI"] = "ON"
        # Build cpptrace as a static PIC library so its objects are merged
        # into libassert.so and no unpackaged libcpptrace.so dependency
        # remains for consumers at runtime.
        tc.variables["CPPTRACE_STATIC"] = "ON"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["assert"]
        # Upstream installs assert.hpp to include/assert/assert/assert.hpp and
        # exposes that directory as its INSTALL_INTERFACE include dir; the
        # internal `#include "../third_party/magic_enum.hpp"` then resolves
        # into include/assert/third_party/ within the same package.
        self.cpp_info.includedirs = ["include/assert/assert"]
        self.cpp_info.set_property("cmake_file_name", "assert")
        self.cpp_info.set_property("cmake_target_name", "assert::assert")
        self.cpp_info.set_property("cmake_target_aliases", ["assert::libassert"])
        self.cpp_info.set_property("pkg_config_name", "libassert")