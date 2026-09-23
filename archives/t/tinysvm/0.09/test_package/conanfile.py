#!/usr/bin/env python3
"""Installed-package consumer tests for TinySVM 0.09."""

import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TinySVMTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
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
        # HMDFS does not support GNU make's FIFO jobserver.
        cmake.build(cli_args=["--parallel", "1"], build_tool_args=["-j1"])

    @staticmethod
    def _run_checked(argv):
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=180, check=False
        )
        if result.returncode != 0:
            raise AssertionError(
                f"command failed ({result.returncode}): {argv!r}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result.stdout + result.stderr

    def test(self):
        if not can_run(self):
            self.output.warning("cross-build: installed-package tests skipped")
            return

        dependency = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dependency.package_folder, "bin")
        tools = {
            name: os.path.join(bindir, name)
            for name in ("svm_learn", "svm_classify", "svm_model")
        }
        for name, executable in tools.items():
            version_text = self._run_checked([executable, "-v"])
            if "0.09" not in version_text:
                raise AssertionError(f"{name} did not report version 0.09")

        workdir = os.path.abspath(os.path.join(self.build_folder, "cli-work"))
        os.makedirs(workdir, exist_ok=True)
        train = os.path.join(workdir, "train.dat")
        test = os.path.join(workdir, "test.dat")
        model = os.path.join(workdir, "model")
        with open(train, "w", encoding="ascii") as stream:
            stream.write(
                "+1 1:2 2:2\n+1 1:2 2:1\n+1 1:1 2:2\n"
                "-1 1:-2 2:-2\n-1 1:-2 2:-1\n-1 1:-1 2:-2\n"
            )
        with open(test, "w", encoding="ascii") as stream:
            stream.write("+1 1:1.5 2:1.5\n-1 1:-1.5 2:-1.5\n")

        self._run_checked([tools["svm_learn"], train, model])
        if not os.path.isfile(model) or os.path.getsize(model) == 0:
            raise AssertionError("svm_learn did not create a non-empty model")

        classification = self._run_checked(
            [tools["svm_classify"], test, model]
        )
        if "Accuracy:   100.00000% (2/2)" not in classification:
            raise AssertionError(f"unexpected classification result: {classification}")

        model_info = self._run_checked([tools["svm_model"], model])
        for expected in ("Number of SVs:", "Size of training data:"):
            if expected not in model_info:
                raise AssertionError(f"svm_model output is missing {expected!r}")

        api_test = os.path.join(self.cpp.build.bindirs[0], "tinysvm_api_test")
        self.run(f'"{api_test}" "{model}"', env="conanrun")
