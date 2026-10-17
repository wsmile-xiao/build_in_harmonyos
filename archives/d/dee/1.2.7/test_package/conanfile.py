#!/usr/bin/env python3
"""Conan test_package — dee 1.2.7 L1 consumer test (R34).

dee is a pkg-config library (no cmake config); the consumer resolves
libdee-1.0 via pkg-config with PKG_CONFIG_PATH pointing at the package's
lib/pkgconfig, and glib-2.0/gobject-2.0 via PkgConfigDeps. R34 exercises the
DeeModel API (create model, set schema, append row, check row count) — a
standalone model needs no live dbus session.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class DeeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("glib/2.84.0.1.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        dee_root = self.dependencies["dee"].package_folder
        toolchain = CMakeToolchain(self)
        toolchain.variables["DEE_ROOT"] = dee_root.replace("\\", "/")
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_dee")
        self.run(test_bin, env="conanrun")
