#!/usr/bin/env python3
"""Consumer and HarmonyOS ABI tests for db1-compat."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Db1CompatTestConan(ConanFile):
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
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        api_test = os.path.join(self.cpp.build.bindirs[0], "db1_api_test")
        ohos_test = os.path.join(self.cpp.build.bindirs[0], "db1_ohos_test")
        self.run(self._test_command(api_test), env="conanrun")
        self.run(self._test_command(ohos_test), env="conanrun")

    def _test_command(self, executable):
        if not cross_building(self):
            return shlex.quote(executable)

        qemu = shutil.which("qemu-aarch64")
        sysroot = os.environ.get("QEMU_LD_PREFIX", "")
        if not qemu or not sysroot:
            raise ConanInvalidConfiguration(
                "Cross execution requires qemu-aarch64 and QEMU_LD_PREFIX"
            )
        return (
            f"{shlex.quote(qemu)} -L {shlex.quote(sysroot)} "
            f"{shlex.quote(executable)}"
        )
