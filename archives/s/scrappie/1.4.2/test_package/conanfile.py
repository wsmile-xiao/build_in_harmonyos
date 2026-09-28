#!/usr/bin/env python3
"""Conan test_package — scrappie L1 consumer test (OHOS aarch64).

Builds a consumer against the packaged scrappie and runs it.

OHOS note: processes whose executable lives on HMDFS (/storage) are denied
exec-mmap of DSOs from non-trusted paths (conan store), so the consumer is
linked fully statically (libscrappie.a + static dep archives) instead of via
the CMakeDeps shared-library targets.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ScrappieTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = []

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _static_lib(dep, filename):
        for d in dep.cpp_info.libdirs:
            if not os.path.isabs(d):
                d = os.path.join(dep.package_folder, d)
            candidate = os.path.join(d, filename)
            if os.path.exists(candidate):
                return candidate
        raise Exception("%s not found in %s" % (filename, dep.package_folder))

    def generate(self):
        deps = self.dependencies
        pkg = deps["scrappie"].package_folder
        static_libs = [os.path.join(pkg, "lib", "libscrappie.a"),
                       self._static_lib(deps["openblas"], "libopenblas.a"),
                       self._static_lib(deps["hdf5"], "libhdf5.a"),
                       self._static_lib(deps["libaec"], "libsz.a")]
        tc = CMakeToolchain(self)
        tc.variables["SCRAPPIE_PKG"] = pkg
        # CMake list of absolute static archives, link order matters
        tc.variables["SCRAPPIE_STATIC_LIBS"] = ";".join(static_libs)
        tc.generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d/R34: execute the built consumer binary directly
        binpath = os.path.join(self.cpp.build.bindirs[0], "test_scrappie")
        self.run(f'"{binpath}"')
