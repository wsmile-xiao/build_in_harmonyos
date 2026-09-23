#!/usr/bin/env python3
"""Conan test package — canlock 3.3.1 (CMake)."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CanlockTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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

    def _test_binary(self, name):
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        return os.path.join(self.cpp.build.bindirs[0], name + suffix)

    def test(self):
        core_test = self._test_binary("test_canlock")
        if not os.path.isfile(core_test):
            raise RuntimeError(f"Expected test executable is missing: {core_test}")

        if can_run(self):
            self.run(f'"{core_test}"', env="conanrun")
            self.run("canlock --version", env="conanrun")
            self.run("canlock-mhp --version", env="conanrun")
            self.run("canlock-hfp --version", env="conanrun")
            if str(self.settings.os) == "OHOS":
                ohos_test = self._test_binary("test_canlock_ohos")
                if not os.path.isfile(ohos_test):
                    raise RuntimeError(
                        f"Expected OHOS test executable is missing: {ohos_test}"
                    )
                self.run(f'"{ohos_test}"', env="conanrun")
        else:
            self.output.info(
                "Cross-built consumer; target-side runtime tests are skipped "
                "in this Conan invocation."
            )
