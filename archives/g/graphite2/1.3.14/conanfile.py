#!/usr/bin/env python3
"""Conan recipe for graphite2 1.3.14 — CMake build system.

graphite2 is a "smart font" system developed by SIL International for
handling the complexities of lesser-known languages of the world.

This recipe enforces R5/R26: static linking by default.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import can_run


class Graphite2Conan(ConanFile):
    name = "graphite2"
    version = "1.3.14"
    description = "Graphite2: a 'smart font' system for lesser-known languages"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/silnrsi/graphite"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Fix: lld linker needs libxml2.so.16 from OHOS SDK llvm/lib directory
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc and os.path.sep in cc:
            cc_real = os.path.realpath(cc)
            llvm_dir = os.path.dirname(os.path.dirname(cc_real))
            llvm_lib = os.path.join(llvm_dir, "lib")
            if os.path.isdir(llvm_lib):
                current = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = llvm_lib + (":" + current if current else "")
        tc = CMakeToolchain(self)
        # R5/R26: build static by default
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # Fix: ensure C++ vtable/typeinfo symbols are exported for static lib
        tc.variables["CMAKE_CXX_VISIBILITY_PRESET"] = "default"
        tc.variables["CMAKE_VISIBILITY_INLINES_HIDDEN"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM must be passed as cache variable
        # because CMake 4.x checks cmake_minimum_required() before processing
        # toolchain file variables.
        cmake.configure(variables={
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
        })
        cmake.build()
        # L1: Run upstream official test suite (83 tests via ctest)
        if can_run(self):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["graphite2"]
        # graphite2 is C++ — requires libc++ runtime when linked from C code
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["c++"]
