#!/usr/bin/env python3
"""Conan test_package — aws-c-io 0.27.5 (CMake).

L1 test: verifies aws-c-io library loads and API can be called.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwsCioTestConan(ConanFile):
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
        # cmake.test() runs CTest without conanrun env; on HarmonyOS CMake
        # lacks Platform/HarmonyOS so RPATH is ineffective, causing the test
        # binary to fail loading libaws-c-io.so and its shared dependencies.
        # Use self.run() with env="conanrun" to ensure LD_LIBRARY_PATH is set.
        #
        # Work around: aws-c-cal's pre-built .so has DT_NEEDED with absolute
        # paths from the build machine's ~/.conan2. On CI workers where
        # CONAN_HOME != ~/.conan2 (e.g. ~/.cache/conan2), create a symlink
        # so the absolute paths resolve.
        default_conan2 = os.path.expanduser("~/.conan2")
        if not os.path.exists(default_conan2):
            actual_home = os.environ.get("CONAN_HOME", "")
            if not actual_home or not os.path.isdir(actual_home):
                cache_conan2 = os.path.expanduser("~/.cache/conan2")
                if os.path.isdir(cache_conan2):
                    actual_home = cache_conan2
            if actual_home and os.path.isdir(actual_home):
                try:
                    os.symlink(actual_home, default_conan2)
                except OSError:
                    pass  # may lack permission

        test_binary = os.path.join(self.cpp.build.bindir, "test_aws_c_io")
        self.run(test_binary, env="conanrun")
