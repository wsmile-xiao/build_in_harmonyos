#!/usr/bin/env python3
"""Conan test_package — googletest 1.17.0."""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GoogletestTestConan(ConanFile):
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
        # OHOS: musl ld.so must resolve libc++_shared.so for the C++ runtime.
        # googletest links statically, so the only runtime deps are
        # libc++_shared.so + libc.so — both in /system/lib64 on every OHOS
        # system. Set a clean LD_LIBRARY_PATH (conanrun's inherited value may
        # contain whitespace that breaks bash word splitting).
        # Wrap with bash like glib2 does (CONFIG_SHELL -> PATH -> hnp bash).
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_googletest")
        if not os.path.isfile(test_bin):
            raise Exception(f"Test binary not found: {test_bin}")
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(
            f'{bash} -c "LD_LIBRARY_PATH=/system/lib64 {test_bin}"',
            env="conanrun",
        )
