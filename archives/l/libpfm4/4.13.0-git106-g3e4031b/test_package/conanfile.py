#!/usr/bin/env python3
"""Conan test_package for libpfm4 (L1 test).

Three consumer programs are built against the *installed* package and run
through CTest:

  test                   - public API: PMU/event discovery, lookup, encoding
  test_upstream_validate - the upstream event table suite (tests/validate.c)
  test_ohos              - HarmonyOS specifics: ABI size constants, perf_events PMU
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libpfm4TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("ctest --output-on-failure",
                 cwd=self.build_folder, env="conanrun")
