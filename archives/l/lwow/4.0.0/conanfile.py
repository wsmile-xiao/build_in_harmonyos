#!/usr/bin/env python3
"""Conan recipe for lwow 4.0.0 — Lightweight OneWire library (C, CMake)."""
import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LwowConan(ConanFile):
    name = "lwow"
    version = "4.0.0"
    description = "Lightweight OneWire protocol library for embedded systems"
    license = "MIT"
    homepage = "https://github.com/MaJerle/lwow"
    url = "https://github.com/MaJerle/lwow"

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
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["LWOW_OPTS_FILE"] = os.path.join(
            self.source_folder, "lwow", "src", "include", "lwow", "lwow_opts_template.h"
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # The lwow/ subdirectory is the standalone library CMake project
        cmake.configure(build_script_folder="lwow")
        cmake.build()

    def package(self):
        # The upstream CMake defines no install rules; install artifacts manually.
        # With cmake_layout, self.build_folder already points to <cache>/b/.../build/Release.
        candidates = [
            os.path.join(self.build_folder, "build", "Release"),
            os.path.join(self.build_folder, "Release"),
            os.path.join(self.build_folder, "lwow"),
            self.build_folder,
        ]
        lib_src = None
        for cand in candidates:
            if os.path.isdir(cand) and any(
                fname.endswith(".a") or fname.endswith(".so")
                for fname in os.listdir(cand)
            ):
                lib_src = cand
                break
        self.output.info("lwow package lib_src=%s build_folder=%s" % (lib_src, self.build_folder))
        if lib_src is None:
            raise ConanException("No built lwow library archive found in build folder")
        copy(self, "*.a", lib_src,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so", lib_src,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", os.path.join(self.source_folder, "lwow", "src", "include"),
             os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "lwow_opts.h", os.path.join(lib_src, "lib_inc"),
             os.path.join(self.package_folder, "include", "lwow"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["lwow_devices", "lwow"]
