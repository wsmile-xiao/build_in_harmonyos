#!/usr/bin/env python3
"""Installed-package consumer test for libunwind 1.6.2."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibunwindTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        if self.settings.os != "OHOS":
            return

        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = tools.get("c", "")
        tool_dir = os.path.dirname(compiler)
        if not tool_dir and os.path.isdir("/data/service/hnp/bin"):
            tool_dir = "/data/service/hnp/bin"
        if tool_dir:
            env = Environment()
            env.prepend_path("PATH", tool_dir)
            env.vars(self).save_script("libunwind_test_ohos_tools")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "NOT_RUN LIBUNWIND_TARGET_CONSUMER=0/1 reason=cross_building"
            )
            return

        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(
            self.cpp.build.bindirs[0], "libunwind_consumer" + suffix
        )
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
