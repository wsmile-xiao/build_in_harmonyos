#!/usr/bin/env python3
"""Conan L1 test for the EGL 1.0.5 OHOS pbuffer and ES3 lifecycle."""
import os
import shlex
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class EglTestConan(ConanFile):
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
        # OHOS /bin/sh (mksh) cannot execute ELF binaries directly.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_bin = os.path.join(self.build_folder, "test_egl")
        command = f"{shlex.quote(bash)} -c {shlex.quote(test_bin)}"
        self.run(command, env="conanrun")
