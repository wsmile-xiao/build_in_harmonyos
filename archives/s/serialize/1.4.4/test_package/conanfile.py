#!/usr/bin/env python3
"""Test package for serialize 1.4.4 (single-header C++ bitpacking serializer).

Conan L1 consumer test. CI runs this automatically via `conan create`.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SerializeTestConan(ConanFile):
    settings = 'os', 'compiler', 'build_type', 'arch'
    generators = 'CMakeDeps', 'VirtualRunEnv'

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: keep OHOS/Linux consumers on the same explicit target triple.
        if self.settings.os in ('Linux', 'OHOS'):
            tc.cache_variables['CMAKE_SYSTEM_NAME'] = 'Linux'
            tc.cache_variables['CMAKE_SYSTEM_PROCESSOR'] = 'aarch64'
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The two cases are executed directly rather than through ctest so the
        # run is explicit in the CI log:
        #   test_serialize      - consumer use of the public API
        #   test_serialize_ohos - HarmonyOS platform-specific assertions
        bindir = self.cpp.build.bindirs[0]
        if cross_building(self):
            # Cross-compiled: the OHOS aarch64 binaries cannot run on the build
            # machine. Execution is covered on the target platform (evidence in
            # notes.md / test_package/MANIFEST.yml).
            self.output.info('cross-building: compile + link verified only')
            return
        self.run(os.path.join(bindir, 'test_serialize'), env='conanrun')
        self.run(os.path.join(bindir, 'test_serialize_ohos'), env='conanrun')
