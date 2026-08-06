#!/usr/bin/env python3
"""Conan consumer test for CUPS 2.4.19."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CupsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindirs[0], "test_cups")
            self.run(executable, env="conanrun")

            dependency = self.dependencies[self.tested_reference_str]
            cups_exec = os.path.join(
                dependency.package_folder,
                "usr", "lib", "cups", "daemon", "cups-exec",
            )
            filter_script = os.path.join(
                self.source_folder, "test_filter_args.sh",
            )
            os.chmod(filter_script, 0o644)
            command = " ".join([
                shlex.quote(cups_exec),
                "none",
                shlex.quote(filter_script),
                "caller-argv0",
                "job-123",
                "currentUser",
                "document-title",
                "1",
                "media=a4",
            ])
            self.run(command, env="conanrun")
