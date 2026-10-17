#!/usr/bin/env python3
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libmpeg3TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        executable = os.path.join(self.cpp.build.bindir, "test_libmpeg3")
        if self.settings.os == "Linux":
            self.run(executable, env="conanrun")
            return
        if self.settings.os != "OHOS":
            return
        env = os.environ.copy()
        subprocess.run([executable], check=True, env=env)
