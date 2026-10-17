#!/usr/bin/env python3
"""Conan recipe for Chipmunk2D (chipmunk-physics) 7.0.3 — CMake.

2D physics library. Demos require GLUT and are always disabled; the
`sys/sysctl.h` include in cpHastySpace.c is Apple-only at use sites and
is guarded accordingly by the platform patch (OHOS musl lacks the header).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ChipmunkPhysicsConan(ConanFile):
    name = "chipmunk-physics"
    version = "7.0.3"
    description = "Chipmunk2D: fast and lightweight 2D rigid body physics library in C"
    license = "MIT"
    homepage = "https://chipmunk2d.net"
    url = "https://github.com/slembcke/Chipmunk2D"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "chipmunk-physics is supported only on Linux/OHOS")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_DEMOS"] = False
        tc.variables["INSTALL_DEMOS"] = False
        tc.variables["BUILD_SHARED"] = bool(self.options.shared)
        tc.variables["BUILD_STATIC"] = not self.options.shared
        tc.variables["INSTALL_STATIC"] = not self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=str(self.source_folder),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["chipmunk"]
