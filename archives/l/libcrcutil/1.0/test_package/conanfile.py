#!/usr/bin/env python3
"""Conan test package — libcrcutil 1.0 installed-library consumers."""

import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibcrcutilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        runner = self._cross_runner()
        if not runner and not can_run(self):
            raise ConanInvalidConfiguration("Target test executables cannot run")
        test_env = Environment()
        if runner:
            test_env.define("QEMU_SET_ENV", self._qemu_set_env())
        with test_env.vars(self).apply():
            for name in ("test_libcrcutil", "test_vectors", "test_ohos"):
                executable = os.path.join(self.cpp.build.bindir, name)
                command = f'"{executable}"'
                if runner:
                    command = f'"{runner}" {command}'
                self.run(command, env="conanrun")

    def _cross_runner(self):
        if str(self.settings.os) != "OHOS":
            return ""
        if platform.machine().lower() in ("aarch64", "arm64"):
            return ""
        runner = shutil.which("qemu-aarch64")
        if not runner:
            raise ConanInvalidConfiguration(
                "Running OHOS AArch64 consumer tests requires qemu-aarch64"
            )
        return runner

    def _qemu_set_env(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = os.path.realpath(compiler_executables.get("cpp", ""))
        sdk_library_path = os.path.join(
            os.path.dirname(os.path.dirname(cxx)), "lib", "aarch64-linux-ohos"
        )
        dependency = self.dependencies[self.tested_reference_str]
        package_library_path = os.path.join(dependency.package_folder, "lib")
        return f"LD_LIBRARY_PATH={package_library_path}:{sdk_library_path}"
