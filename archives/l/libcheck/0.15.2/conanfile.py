#!/usr/bin/env python3
"""Conan recipe for libcheck 0.15.2 — CMake build (cross-compile friendly).

libcheck 0.15.2 ships both Autotools and CMake build systems. The Autotools
path is blocked on OHOS by two compounding issues:

  1. config.guess / config.sub (2014-11-04) do not recognise the OHOS
     target triple ``aarch64-unknown-linux-ohos`` (see patches/0001-*).
  2. config.status creates a temp script (``./confXXXXXX/subs*.awk``)
     without the execute bit, and the OHOS build filesystem does not
     grant +x on newly created files, so autotools.configure() dies with
     ``Permission denied``.

The CMake path (CMake 3.9+, project LANGUAGES C) avoids both problems:
no config.guess, no config.status temp scripts. We use the CMake build
system and remove the autotools-specific --build/--host override (CMake
Toolchain handles the cross-compile via CMAKE_SYSTEM_NAME=OHOS).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout


class LibcheckConan(ConanFile):
    name = "libcheck"
    version = "0.15.2"
    description = "Unit testing framework for C"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libcheck/check"
    url = "https://github.com/libcheck/check"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Avoid building Check's own test suite (it is the upstream test
        # executable and would need to run on the target, not at cross-
        # compile time).
        tc.variables["CHECK_ENABLE_TESTS"] = "OFF"
        tc.variables["CHECK_ENABLE_SUBUNIT"] = "OFF"
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy the pkg-config template that CMake does not install by default
        copy(self, "check.pc", src=self.source_folder, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["check"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
