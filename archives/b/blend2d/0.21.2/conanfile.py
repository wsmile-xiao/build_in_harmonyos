#!/usr/bin/env python3
"""Conan recipe for blend2d 0.21.2 (CMake).

blend2d is a high-performance 2D vector graphics engine with JIT compiler.
It requires asmjit (with ujit module) which is downloaded separately from
GitHub since GitHub archives don't include git submodules.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Blend2DConan(ConanFile):
    name = "blend2d"
    version = "0.21.2"
    description = "High-performance 2D vector graphics engine with JIT compiler"
    license = "Zlib"
    homepage = "https://blend2d.com"
    url = "https://github.com/blend2d/blend2d"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"blend2d is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download and extract blend2d source
        get(self, **self.conan_data["sources"], strip_root=True)

        # Download and extract asmjit into 3rdparty/asmjit
        # blend2d expects asmjit in 3rdparty/asmjit for the ujit module
        asmjit_dir = os.path.join(self.source_folder, "3rdparty", "asmjit")
        os.makedirs(asmjit_dir, exist_ok=True)
        get(self, **self.conan_data["asmjit"], strip_root=True,
            destination=asmjit_dir)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # blend2d uses its own BLEND2D_STATIC option instead of BUILD_SHARED_LIBS
        tc.variables["BLEND2D_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["BLEND2D_TEST"] = "OFF"
        tc.variables["BLEND2D_DEMOS"] = "OFF"
        tc.variables["BLEND2D_NO_INSTALL"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Headers installed to include/blend2d/blend2d.h
        # Add include/blend2d so consumers can #include <blend2d.h>
        self.cpp_info.includedirs = ["include", "include/blend2d"]
        self.cpp_info.libs = ["blend2d"]
        # blend2d links to libc, pthread, and libm (detected by CMake)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["c", "m", "pthread"]
