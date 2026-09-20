#!/usr/bin/env python3
"""Conan test_package for pgexporter 0.8.0."""
import os
import shlex
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PgexporterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-compiling: skipping binary execution test")
            return
        dep = self.dependencies["pgexporter"]
        bindir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
        if not os.path.isabs(bindir):
            bindir = os.path.join(dep.package_folder, bindir)
        env = {"PATH": bindir + os.pathsep + os.environ.get("PATH", "")}
        prefix = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_pgexporter")
        self.run(f"{prefix} {shlex.quote(bin_path)}", env="conanrun")
