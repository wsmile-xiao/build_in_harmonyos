#!/usr/bin/env python3
"""Conan recipe for itpp 4.3.1 — IT++ mathematical signal-processing library
(C++, CMake build).

Known OHOS quirks handled here:
  * the sdist root contains a file named `version` — it shadows the C++
    standard header <version> via -I include paths (libcxx internal
    includes) → rename it to version.txt before configuring.
  * BLAS/LAPACK are optional probes (find_package); OHOS has no BLAS here,
    so the build proceeds without them (some BLAS-dependent gtests crash —
    recorded honestly in the PR).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get)
from conan.tools.layout import basic_layout


class ItppConan(ConanFile):
    name = "itpp"
    version = "4.3.1"
    description = "IT++ — C++ library of mathematical, signal processing and communication functions"
    license = "GPL-3.0"
    homepage = "https://sourceforge.net/projects/itpp/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    package_type = "library"

    export_sources = ["patches/*"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # Rename the `version` file so it does not shadow <version> (libcxx
        # internal include) during compilation.
        ver = os.path.join(self.source_folder, "version")
        if os.path.isfile(ver) and not os.path.isfile(ver + ".txt"):
            shutil.move(ver, ver + ".txt")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["ITPP_SHARED_LIB"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # itpp 4.3.1 uses the removed `register` keyword (C++17) → -Wno-register
        tc.variables["CMAKE_CXX_FLAGS"] = "-Wno-register"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        lib = os.path.join(self.package_folder, "lib", "libitpp_static.a")
        hdr = os.path.join(self.package_folder, "include", "itpp", "itbase.h")
        if not os.path.isfile(lib):
            raise ConanException(f"libitpp_static.a missing in {self.package_folder}")
        if not os.path.isfile(hdr):
            raise ConanException(f"itpp/itbase.h missing: {hdr}")

    def package_info(self):
        self.cpp_info.libs = ["itpp_static"]
