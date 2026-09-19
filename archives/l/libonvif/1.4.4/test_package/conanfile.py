#!/usr/bin/env python3
"""Conan test_package - libonvif consumer test (L1).

Builds a real consumer program against the packaged library (public header
onvif.h + shared library onvif) and runs it. The program exercises
offline-safe exported C API functions and asserts observable behavior;
its exit code decides the test result (R34: no print-only stub).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibonvifTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # onvif links libxml2 dynamically and musl ignores DT_RUNPATH, so
        # aggregate the absolute lib dirs of the whole dependency graph for
        # the run (cpp_info.libdirs entries are package-relative).
        ldpaths = []
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                if path not in ldpaths:
                    ldpaths.append(path)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libonvif")
        self.run('LD_LIBRARY_PATH="%s" ctest --output-on-failure' % ":".join(ldpaths),
                 cwd=self.build_folder, env="conanbuild")
