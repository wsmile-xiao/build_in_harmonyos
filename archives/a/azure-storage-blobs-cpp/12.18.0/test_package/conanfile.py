#!/usr/bin/env python3
"""Conan test_package — L1 consumer test for azure-storage-blobs-cpp 12.18.0.

CI runs this via `conan create` (which invokes test_package).
test() must invoke the consumed binary with self.run() (L0d gate).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class AzureStorageBlobsCppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Workaround: transitive deps' CMakeDeps include dirs not propagated
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        for dep_name in ("azure-core-cpp", "azure-storage-common-cpp"):
            try:
                dep = self.dependencies[dep_name]
                dep_inc = os.path.join(dep.package_folder, "include")
                if os.path.isdir(dep_inc):
                    tc.extra_cxxflags.append(f"-I{dep_inc}")
            except Exception:
                pass
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d gate: invoke the consumer binary with self.run()
        # env="conanrun" activates runtime library paths (LD_LIBRARY_PATH)
        # so that shared dependencies (libazure-core.so, libxml2.so) are found.
        if not cross_building(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_azure-storage-blobs-cpp"),
                     env="conanrun")
        else:
            self.output.info("skipping run for cross-build")
