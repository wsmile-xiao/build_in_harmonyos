#!/usr/bin/env python3
"""Consumer tests for quadrule 0-20121001."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class QuadruleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        executable = os.path.join(self.cpp.build.bindir, "quadrule_tests")
        if can_run(self):
            self.run(
                "ctest --output-on-failure -C {}".format(self.settings.build_type),
                cwd=self.build_folder,
                env="conanrun",
            )
            return

        runner = os.getenv("QUADRULE_TEST_RUNNER")
        if not runner:
            raise ConanInvalidConfiguration(
                "Cross-built tests require QUADRULE_TEST_RUNNER; "
                "the native HarmonyOS CI executes them directly"
            )
        scenarios = (
            "legendre",
            "hermite",
            "laguerre",
            "clenshaw_curtis",
            "rule_adjust",
            "helpers",
            "summer",
            "ohos_aarch64_abi",
        )
        for scenario in scenarios:
            self.run(
                '{} "{}" {}'.format(runner, executable, scenario),
                env="conanrun",
            )
