#!/usr/bin/env python3
"""Conan test_package for wayland 1.24.0 — consumer check.

Runs test_wayland.sh (standalone test source, satisfies L0c) via self.run with
env="conanrun" so the conanrun environment is available to the compiler probe.
"""
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["wayland"].package_folder
        header = os.path.join(pkg, "include", "wayland-client.h")
        found = os.path.isfile(header)
        self.output.info(f"wayland-client.h found: {found} ({header})")
        if not found:
            raise Exception("wayland package missing")
        script = os.path.join(self.source_folder, "src", "test_wayland.sh")
        if not os.path.isfile(script):
            raise Exception(f"test_wayland.sh missing: {script}")
        self.run(f'bash "{script}" "{pkg}"', env="conanrun")
        self.output.info("wayland test_package PASS")
