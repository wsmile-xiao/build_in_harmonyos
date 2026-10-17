#!/usr/bin/env python3
"""Conan test_package for libdontdie — consumer-side behaviour test.

libdontdie has no exported API and no public header: it intercepts
socket(2) when preloaded.  The consumer program is therefore built
stand-alone and executed with LD_PRELOAD pointing at the packaged
library; the assertions on SO_KEEPALIVE / TCP_KEEPALIVE decide the
exit code.  LD_PRELOAD must carry an absolute path — musl ignores
DT_RUNPATH, so the conanrun environment alone is not sufficient.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdontdieTestConan(ConanFile):
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
        dep = self.dependencies["libdontdie"]
        lib = os.path.join(dep.package_folder, "lib", "libdontdie.so")
        consumer = os.path.join(self.cpp.build.bindirs[0], "dd_consumer")
        self.run(
            f'LD_PRELOAD="{lib}" DD_TCP_KEEPALIVE_TIME=7 "{consumer}"')
