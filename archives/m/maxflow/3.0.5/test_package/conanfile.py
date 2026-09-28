#!/usr/bin/env python3
"""Conan test_package — maxflow 3.0.5"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class MaxflowTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def generate(self):
        # Same runner-env constraint as the parent recipe: bare cmake/ctest
        # do not resolve outside the hnp tool dirs (r5 device run).
        env = Environment()
        for d in ("/data/service/hnp/cmake.org/cmake_4.1.2/bin",
                  "/data/service/hnp/bin"):
            if os.path.isdir(d):
                env.prepend_path("PATH", d)
        env.vars(self, scope="build").save_script("conanbuild_hnp_path")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the consumer binary built in build().  test_maxflow.cpp
        # drives the installed maxflow::maxflow target (int + double graph
        # instantiations, maxflow() flow values and what_segment()
        # segmentation) and returns 0 on success.
        # L0d gate requires a literal self.run() in test() (CI L0d rejects a
        # bare cmake.test() as a possible stub).
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_maxflow"),
            env="conanrun",
        )
