#!/usr/bin/env python3
"""Conan recipe for pxlib 0.6.9 on HarmonyOS PC (OHOS aarch64).

pxlib is a C library for reading/writing Paradox database files.
Build system: CMake.

Upstream quirks fixed at build time (see conandata.yml patches):
  - CMakeLists.txt has no install() rules  -> package() copies artifacts.
  - Version macro is pinned to 0.6.8 in the release tarball -> aligned
    to the 0.6.9 tag (0001).
  - add_library() hardcodes SHARED -> honors the conan shared option
    (0002).

Dependencies: iconv (OHOS musl system library), libgsf-1 (optional, disabled).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PxlibConan(ConanFile):
    name = "pxlib"
    version = "0.6.9"
    description = "Library for reading and writing Paradox database files"
    license = "LGPL-2.1"
    homepage = "https://pxlib.sourceforge.net/"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # iconv is provided by the OHOS musl system libc; no conan dependency.
        # libgsf-1 is optional upstream (ENABLE_GSF, default OFF) — not enabled.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream CMakeLists.txt defines no install() rules: copy the
        # built library and the public headers explicitly.
        lib_suffix = ".so" if self.options.shared else ".a"
        copy(
            self,
            f"libpxlib{lib_suffix}",
            self.build_folder,
            os.path.join(self.package_folder, "lib"),
        )
        # Public API is the build-time generated paradox.h / paradox-gsf.h
        # (configure_file output with @PX_HAVE_ICONV@ etc. substituted) and
        # pxversion.h. The *.h.in templates must NOT be shipped: they are
        # pre-substitution and would shadow the real headers for consumers.
        copy(self, "paradox.h", os.path.join(self.build_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "paradox-gsf.h", os.path.join(self.build_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "pxversion.h", self.build_folder,
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["pxlib"]
