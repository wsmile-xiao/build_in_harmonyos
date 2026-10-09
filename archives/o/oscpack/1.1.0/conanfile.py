#!/usr/bin/env python3
"""Conan recipe — oscpack 1.1.0 (C++ Open Sound Control packet library).

Oscpack is a small C++ library for packing/unpacking OSC packets with
minimal UDP networking classes for POSIX. Upstream provides a CMakeLists
without install rules — our patch adds them (library + headers, keeping
the source-root-relative include layout: "osc/OscTypes.h", "ip/...").

OHOS adaptation notes:
- aarch64 is LP64: upstream OscTypes.h assumes "non-x86_64 => 32-bit"
  (typedef long int32). Patches fix int32/uint32 to int-based typedefs
  and drop the now-duplicate int overloads on LP64.
- No external dependencies (POSIX sockets come from libc).

R32 note: the OHOS-adapted conan maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS
via CMakeToolchain — no settings.os branch needed.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OscpackConan(ConanFile):
    name = "oscpack"
    version = "1.1.0"
    description = "Oscpack: a simple C++ library for packing and unpacking OSC (Open Sound Control) packets"
    license = "MIT"
    homepage = "http://www.rossbencina.com/code/oscpack"
    url = "https://github.com/rossbencina/oscpack"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # pure C++, POSIX sockets only — no third-party dependencies
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: system-name libraries default to static linking
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        if not self.options.shared:
            tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        # upstream declares cmake_minimum_required(VERSION 2.6);
        # CMake >= 4 removed compatibility with < 3.5. Must be a cache
        # variable (command line), not a plain toolchain variable —
        # cmake_minimum_required is processed before project() and would
        # never see a value set inside conan_toolchain.cmake.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "oscpack")
        self.cpp_info.set_property("cmake_target_name", "oscpack::oscpack")
        self.cpp_info.libs = ["oscpack"]
