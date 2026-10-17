#!/usr/bin/env python3
"""Test package for libzmq 4.3.5 — HarmonyOS consumer validation."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibzmqTestConan(ConanFile):
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
        env = Environment()
        if self.settings.os == "OHOS":
            # The OHOS musl loader stops searching the remaining
            # LD_LIBRARY_PATH entries once it walks the huge
            # /data/storage/el1/bundle/libs/arm64 directory that the
            # default shell environment appends, which hides the system
            # libc++_shared.so in /system/lib64. Prepend /system/lib64 so
            # the C++ runtime resolves before that path is consulted.
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_package"),
                env="conanrun",
            )

