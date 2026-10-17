#!/usr/bin/env python3
"""Conan recipe — libdecaf 1.0.2 (Ed448-Goldilocks / Curve25519 crypto library).

CMake build. No external dependencies. Builds the decaf library
(shared and/or static) plus its generated public headers.
OHOS adaptation:
- CMAKE_SYSTEM_NAME=HarmonyOS + CMAKE_SYSTEM_PROCESSOR=aarch64 (repo
  convention); combined with the arch-detection patch this selects the
  upstream arch_ref64 code path on aarch64.
- ENABLE_STRICT=OFF: upstream defaults to -Werror and newer clang flags
  -Wdeprecated-copy inside the generated C++ headers.
- The build regenerates public headers with the Python interpreter
  (FindPythonInterp), so python3 must be available at build time.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibdecafConan(ConanFile):
    name = "libdecaf"
    version = "1.0.2"
    description = ("Ed448-Goldilocks / Curve25519 elliptic curve cryptography "
                   "library implementing the Decaf point compression protocol")
    license = "MIT"
    homepage = "https://sourceforge.net/projects/ed448goldilocks/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream builds its shared/static targets from its own options
        tc.variables["ENABLE_SHARED"] = bool(self.options.shared)
        tc.variables["ENABLE_STATIC"] = not self.options.shared
        # Upstream defaults to -Werror; newer clang warns -Wdeprecated-copy
        # on the generated C++ headers, so keep strict warnings off
        tc.variables["ENABLE_STRICT"] = False
        # Cross toolchain per repo convention (applied when the target OS is
        # OHOS); the arch-detection patch uses this aarch64 value to select
        # the upstream arch_ref64 code path
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "HarmonyOS"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch))
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
        self.cpp_info.libs = ["decaf"]
        # Public headers are installed under include/decaf (consumers
        # include <decaf.h> / <decaf/point_448.h>), matching the upstream
        # CMake interface include dir of include/decaf
        self.cpp_info.includedirs = ["include/decaf"]
