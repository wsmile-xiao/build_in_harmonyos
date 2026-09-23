#!/usr/bin/env python3
"""Packaged-consumer tests for boost1.84-stacktrace_noop."""

import os
import subprocess
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BoostStacktraceNoopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BOOST_NOOP_TEST_OHOS"] = (
            str(self.settings.os) == "OHOS"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        bindir = self.cpp.build.bindirs[0]
        general = os.path.abspath(os.path.join(
            self.build_folder,
            bindir, "test_boost1_84_stacktrace_noop" + suffix
        ))

        hdc = os.environ.get("BOOST_STACKTRACE_NOOP_HDC")
        if not hdc:
            CMake(self).test()
            self.run(f'"{general}"', env="conanrun", cwd=self.build_folder)
        else:
            self._run_with_hdc(general, "consumer_general")

        if str(self.settings.os) == "OHOS":
            ohos = os.path.abspath(os.path.join(
                self.build_folder,
                bindir, "test_boost1_84_stacktrace_noop_ohos" + suffix
            ))
            if hdc:
                self._run_with_hdc(ohos, "consumer_ohos")
            else:
                self.run(f'"{ohos}"', env="conanrun", cwd=self.build_folder)

    def _run_with_hdc(self, executable, label):
        runner = os.path.join(self.recipe_folder, "hdc_runner.py")
        remote_base = os.environ.get(
            "BOOST_STACKTRACE_NOOP_HDC_REMOTE_DIR",
            "/data/local/tmp/boost_stacktrace_noop_1_84_0",
        ).rstrip("/")
        command = [
            sys.executable,
            runner,
            "--hdc",
            os.environ["BOOST_STACKTRACE_NOOP_HDC"],
            "--remote-dir",
            f"{remote_base}/consumer",
            "--label",
            label,
            "--timeout",
            "300",
        ]
        target = os.environ.get("BOOST_STACKTRACE_NOOP_HDC_TARGET")
        if target:
            command.extend(["--target", target])
        command.append(executable)
        result = subprocess.run(
            command,
            cwd=self.build_folder,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"HarmonyOS HDC test failed for {label}: {result.returncode}"
            )
