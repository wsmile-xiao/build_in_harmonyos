#!/usr/bin/env python3
"""Conan recipe — mkvalidator 0.6.0 (CMake)

mkvalidator is a Matroska container format validation tool that checks
MKV/WebM file structural integrity. It detects EBML header errors,
invalid SegmentUID, missing track info, and other Matroska format issues.

The project uses CMake and vendors all dependencies (corec, ebml2,
matroska2, zlib, bzlib) as static libraries — no external Conan deps.

Key adaptation points:
- CMAKE_SYSTEM_NAME=Linux is required so UNIX macro is defined, otherwise
  corec selects str_linux.c (glibc-only) instead of str_os.c (portable
  POSIX), causing undefined reference errors.
- corec/tests subdirectory must be disabled (patch 0001) because test
  executables depend on undefined tchar symbols under musl.
- mkvalidator/CMakeLists.txt lacks install rules (patch 0002 adds them).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MkvalidatorConan(ConanFile):
    name = "mkvalidator"
    version = "0.6.0"
    description = "Matroska container format validation tool for MKV/WebM files"
    license = "BSD-2-Clause"
    homepage = "https://www.matroska.org/downloads/mkvalidator.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # mkvalidator is a CLI tool, not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: platform check must include OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mkvalidator only supports Linux/OHOS, got {self.settings.os}"
            )
        tc = CMakeToolchain(self)
        # CMAKE_SYSTEM_NAME=Linux is required: without it the UNIX macro is
        # undefined, causing corec to select str_linux.c (glibc-only) instead
        # of str_os.c (portable POSIX), producing undefined reference errors.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM must be on the cmake command line (not
        # toolchain file) because cmake_minimum_required() checks it before
        # processing the toolchain file. mkvalidator uses cmake_minimum_required
        # (VERSION 2.x) which CMake >= 3.27 rejects without this override.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # mkvalidator is a CLI tool — binary in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
