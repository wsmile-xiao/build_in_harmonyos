#!/usr/bin/env python3
"""Consumer and fault-injection tests for acf-skins 0.6.0."""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AcfSkinsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dependency = self.dependencies["acf-skins"]
        root = os.path.join(dependency.package_folder, dependency.cpp_info.resdirs[0])
        packaged_files = sum(len(files) for _, _, files in os.walk(root))
        if packaged_files != 81:
            raise ConanException(
                f"Expected 81 packaged skin resources, found {packaged_files}"
            )
        if not can_run(self):
            self.output.info(
                "Cross-built skin_probe; run all three scenarios with the packaged "
                "resources on the HarmonyOS PC emulator."
            )
            return

        executable = os.path.join(self.cpp.build.bindir, "skin_probe")
        self.run(f'"{executable}" "{root}"', env="conanrun")
        corrupt = os.path.join(self.source_folder, "corrupt.png")
        self.run(f'"{executable}" --expect-invalid "{corrupt}"', env="conanrun")
        missing = os.path.join(self.source_folder, "missing-corrupt.png")
        result = subprocess.run(
            [executable, "--expect-invalid", missing],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 or "FAIL: cannot read:" not in result.stderr:
            raise ConanException(
                "A missing fault-injection fixture must fail as an I/O error; "
                f"exit={result.returncode}, stdout={result.stdout!r}, "
                f"stderr={result.stderr!r}"
            )
        self.output.info("Missing fault-injection fixture correctly failed as I/O")
