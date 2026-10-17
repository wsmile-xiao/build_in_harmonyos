#!/usr/bin/env python3
"""Conan test_package for enkiTS 1.12 (L1 official test).

Exercises the enkiTS C task-scheduler API: create a TaskScheduler, Initialize
it (spawning worker threads), schedule a parallel TaskSet that sums a range of
integers, wait for completion, verify the parallel sum matches a serial
reference, then shut down and delete the scheduler. CI runs this
automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EnkitsTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # R5: OHOS /system/bin/sh (mksh) cannot exec ELF binaries directly;
        # run the test binary via bash as a belt-and-braces check.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} -c "./test_enkits"', env="conanrun")
