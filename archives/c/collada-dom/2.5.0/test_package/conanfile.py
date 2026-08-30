#!/usr/bin/env python3
"""Conan test_package — collada-dom 2.5.0 consumer test (C++).

R34: test must actually consume the packaged library API. This test builds a
tiny COLLADA 1.4/1.5 document in memory via DAE::load() and queries the parsed
root element, exercising the collada-dom2.5-dp library end to end.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ColladaDomTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Transitive deps of the library headers (boost) — consumed via the
        # package's cpp_info.requires automatically; listed for clarity.
        self.requires("boost/1.90.0.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # E298: do not delegate to CTest (cmake.test()) — CTest runs the
        # consumer without the Conan run environment, so a consumer that links
        # packaged shared libraries fails to load them ("Error loading shared
        # library"). Run the packaged consumer binary explicitly with the
        # conanrun environment activated (LD_LIBRARY_PATH points at the
        # package + dependency lib dirs).
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_collada_dom")
        self.run(f'"{test_bin}"', env="conanrun", cwd=self.build_folder)