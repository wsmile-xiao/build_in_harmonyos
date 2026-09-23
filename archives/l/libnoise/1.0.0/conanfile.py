#!/usr/bin/env python3
"""Conan recipe for libnoise 1.0.0 on HarmonyOS (OHOS).

libnoise is Jason Bevins' portable coherent noise-generating C++ library
(35 translation units, headers under noise/src).  The upstream 1.0.0 source
release builds through hand-written recursive Makefiles that shell out to
libtool in their compile rules; libtool is not part of the OHOS build
environment, so this recipe ships a minimal CMakeLists.txt (exported with the
recipe) that compiles and installs the exact same source and header set.
No upstream source file is modified and no patch is required: every source
file compiles as-is with the OHOS SDK clang in C++17 mode.

The 1.0.0 release ships no test suite of its own (the zip contains only
doc/, include/, lib/, src/ and win32/ MSVC project files), so verification is
the installed-package consumer test in test_package/ - see notes.md for the
upstream inventory evidence.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibnoiseConan(ConanFile):
    name = "libnoise"
    version = "1.0.0"
    description = (
        "A portable, open-source, coherent noise-generating library for C++ "
        "(Perlin, ridged multifractal, billow and Voronoi modules with "
        "terrain/texture model helpers)"
    )
    license = "LGPL-2.1-only"
    homepage = "https://libnoise.sourceforge.net/"
    url = ""  # CI fills this
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The 1.0.0 zip has two top-level entries (COPYING.txt and noise/),
        # so a single-root strip would fail; the exported CMakeLists.txt
        # addresses the sources under their natural noise/ prefix instead.
        get(self, **self.conan_data["sources"], strip_root=False)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream builds both libnoise.a and libnoise.so.0.3; the Conan
        # option decides which flavour this package ships.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream 1.0.0 has no test target (no check goal in any Makefile);
        # the consumer test in test_package/ exercises the installed library.

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["noise"]
