#!/usr/bin/env python3
"""Conan recipe for BCUnit 3.0.2 on HarmonyOS (OHOS).

BCUnit is a C unit testing framework forked from CUnit by Belledonne
Communications (Linphone stack; consumed by bctoolbox).  Upstream primary
build system is CMake with no third-party dependencies.

OHOS-specific handling (evidence in notes.md):
- CMakeLists.txt minimum version raised 2.8.12 -> 3.5 because CMake >= 4
  removed compatibility with cmake_minimum_required(< 3.5)
  (patches/0001-cmake-minimum-version-3.5.patch)
- CU_trace_handler storage moved from Basic/Basic.c into framework Util.c so
  the upstream self-test program (ENABLE_TEST=ON) links again
  (patches/0002-move-cu-trace-handler-to-framework.patch)
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)

required_conan_version = ">=2.0"


class BcunitConan(ConanFile):
    name = "bcunit"
    version = "3.0.2"
    description = (
        "C unit testing framework forked from CUnit by Belledonne "
        "Communications (static/shared library with basic, automated and "
        "console interfaces)"
    )
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/BelledonneCommunications/bcunit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("unit-testing", "testing", "framework", "c")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # bcunit is self-contained: no third-party dependencies
        # (upstream CMakeLists.txt/README declare none and configure links libc only).
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Map the Conan shared option onto upstream's own library toggles
        # (upstream builds bcunit shared + bcunit-static from the same sources).
        tc.variables["ENABLE_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENABLE_STATIC"] = "OFF" if self.options.shared else "ON"
        # Keep the package to the library itself: internal test program,
        # example programs, doxygen docs and curses interface stay disabled
        # (all are upstream defaults except ENABLE_TEST which is used only
        # for the dedicated upstream-test build, see notes.md).
        tc.variables["ENABLE_TEST"] = "OFF"
        tc.variables["ENABLE_EXAMPLES"] = "OFF"
        tc.variables["ENABLE_DOC"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream configures bcunit.pc with *relative* dirs (empty prefix,
        # exec_prefix=bin, libdir=lib, -Llib / -Iinclude) because
        # CMakeLists.txt assigns CMAKE_INSTALL_BINDIR/LIBDIR directly.
        # Anchor every path at the package folder so the file is usable as
        # installed.  Ordered replacements: the bare prefix line first, the
        # longer exec_prefix line before any substring collisions.
        pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", "bcunit.pc")
        pc = load(self, pc_path)
        pc = pc.replace("prefix=\n", f"prefix={self.package_folder}\n", 1)
        pc = pc.replace("exec_prefix=bin\n", "exec_prefix=${prefix}/bin\n", 1)
        pc = pc.replace("libdir=lib\n", "libdir=${prefix}/lib\n", 1)
        pc = pc.replace("includedir=include\n", "includedir=${prefix}/include\n", 1)
        pc = pc.replace("Libs: -Llib -lbcunit\n", "Libs: -L${prefix}/lib -lbcunit\n", 1)
        pc = pc.replace("Cflags: -Iinclude\n", "Cflags: -I${prefix}/include\n", 1)
        save(self, pc_path, pc)

    def package_info(self):
        # Products match upstream install(): headers under include/BCUnit
        # (consumed as #include "BCUnit/BCUnit.h"), lib/libbcunit.so and
        # lib/libbcunit.a; no executables are installed.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["bcunit"]
        self.cpp_info.set_property("pkg_config_name", "bcunit")
