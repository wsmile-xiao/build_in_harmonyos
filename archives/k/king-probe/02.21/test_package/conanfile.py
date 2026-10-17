#!/usr/bin/env python3
"""Native consumer tests; cross builds must explicitly run tests on their target."""
import os
import shlex
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KingProbeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        tc.variables["EXPECT_OHOS"] = str(self.settings.os) == "OHOS"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        suffix = ".exe" if self.settings.os == "Windows" else ""
        package = self.dependencies["king-probe"].package_folder
        probe = os.path.abspath(os.path.join(package, "bin", "probe" + suffix))
        helper = os.path.abspath(os.path.join(
            self.build_folder, self.cpp.build.bindirs[0], "platform_probe" + suffix))
        for path in (probe, helper):
            if not os.path.isfile(path):
                raise ConanException("Required executable missing: " + path)
        if not can_run(self):
            raise ConanException("Target cannot run here. Execute conan test natively on the target; "
                                 "use conan create --test-folder= only for an explicit build-only run.")
        command = [sys.executable, os.path.join(self.recipe_folder, "test_probe.py"),
                   "--probe", probe, "--platform-probe", helper,
                   "--target-os", str(self.settings.os)]
        rendered = subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)
        self.run(rendered, env=None)
