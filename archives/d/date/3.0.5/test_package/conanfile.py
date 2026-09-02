#!/usr/bin/env python3
"""Consumer test for date."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class DateTestConan(ConanFile):
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
        if can_run(self):
            executable = os.path.join(
                self.cpp.build.bindirs[0], "test_date"
            )
            # OHOS consumers link against the platform libc++_shared.so which
            # lives in /system/lib64.  Pin the loader path explicitly so the
            # test binary stays runnable even when the ambient
            # LD_LIBRARY_PATH is malformed on the host shell.
            test_env = Environment()
            test_env.define("LD_LIBRARY_PATH", "/system/lib64")
            with test_env.vars(self).apply():
                self.run(executable, env="conanrun")
