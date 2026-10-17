#!/usr/bin/env python3
"""Conan test_package — watcher 0.14.5 consumer smoke test."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class WatcherTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()

        dep = self.dependencies["watcher"]
        bindir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])
        version_exe = os.path.join(bindir, "wtr.watcher")
        if self.settings.os == "Windows":
            version_exe += ".exe"
        if not os.path.isfile(version_exe):
            raise ConanException(f"missing packaged executable: {version_exe}")

        version_out = os.path.join(self.build_folder, "wtr_watcher_version.txt")
        self.run(f'"{version_exe}" --version > "{version_out}"', env="conanrun")
        with open(version_out, "r", encoding="utf-8") as f:
            output = f.read().strip()
        if str(self.dependencies["watcher"].ref.version) not in output:
            raise ConanException(f"unexpected wtr.watcher --version output: {output}")
