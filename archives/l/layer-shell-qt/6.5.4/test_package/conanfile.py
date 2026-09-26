#!/usr/bin/env python3
"""Consumer test for the installed LayerShellQt C++ API."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LayerShellQtTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        runtime_libdirs = []
        for dependency in self.dependencies.host.values():
            if dependency.package_folder:
                libdir = os.path.join(dependency.package_folder, "lib")
                if os.path.isdir(libdir) and libdir not in runtime_libdirs:
                    runtime_libdirs.append(libdir)
        toolchain.cache_variables["CMAKE_BUILD_RPATH"] = ";".join(runtime_libdirs)
        toolchain.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.cpp.build.bindir, "test_layer_shell_qt")
        runtime_libdirs = []
        for dependency in self.dependencies.host.values():
            if dependency.package_folder:
                libdir = os.path.join(dependency.package_folder, "lib")
                if os.path.isdir(libdir) and libdir not in runtime_libdirs:
                    runtime_libdirs.append(libdir)
        runtime_ld_path = ":".join(runtime_libdirs)
        self.run(
            f'LD_LIBRARY_PATH="{runtime_ld_path}:${{LD_LIBRARY_PATH:-}}" '
            f'QT_QPA_PLATFORM=offscreen "{binary}"'
        )
