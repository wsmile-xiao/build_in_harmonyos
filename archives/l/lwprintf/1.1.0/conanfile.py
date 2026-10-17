#!/usr/bin/env python3
"""Conan recipe — lwprintf 1.1.0 (C11 lightweight printf/sprintf library).

Upstream build is CMake (lwprintf/library.cmake). The root CMakeLists.txt
only adds a Windows-oriented dev/test executable (dev/main.c + win32 port +
tests/test.c) when configured as top-level; this recipe builds only the
portable `lwprintf` static library target, which has no external
dependencies and no OS port requirement (LWPRINTF_CFG_OS=0 default).
Upstream defines no install() rules, so headers and the built archive are
packaged explicitly. The generated lwprintf_opts.h (configure_file from the
template) is installed next to the other public headers so consumers can
`#include "lwprintf/lwprintf.h"`.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LwprintfConan(ConanFile):
    name = "lwprintf"
    version = "1.1.0"
    description = "Lightweight printf and sprintf library for embedded systems (C11)"
    license = "MIT"
    homepage = "https://github.com/MaJerle/lwprintf"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # lwprintf is dependency-free (single self-contained C file)
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: default to static; shared only when explicitly requested
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Build only the portable library target; the upstream dev/test
        # executable (dev/main.c + lwprintf_sys_win32.c) is Windows-only
        # (includes windows.h) and is not part of the OHOS package.
        cmake.build(target="lwprintf")

    def package(self):
        cmake = CMake(self)
        # Upstream has no install() rules; copy headers + archive manually.
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "lwprintf", "src", "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        # Generated lwprintf_opts.h lands in the build dir lib_inc/
        copy(self, "lwprintf_opts.h",
             src=os.path.join(self.build_folder, "lwprintf", "lib_inc"),
             dst=os.path.join(self.package_folder, "include", "lwprintf"),
             keep_path=False)
        for pat in ("*.a", "*.so", "*.so.*"):
            copy(self, pat,
                 src=os.path.join(self.build_folder, "lwprintf"),
                 dst=os.path.join(self.package_folder, "lib"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["lwprintf"]
        self.cpp_info.set_property("cmake_file_name", "lwprintf")
        self.cpp_info.set_property("cmake_target_name", "lwprintf::lwprintf")
