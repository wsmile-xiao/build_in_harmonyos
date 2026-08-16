#!/usr/bin/env python3
"""Conan test_package for glib 2.88.0 — Conan L1 official test.

Builds test_glib.c with CMake (CMakeDeps + CMakeToolchain) and runs it.
The test calls real GLib/GObject/GIO API (string utils, hash table, GVariant,
GObject type system, GIO settings) — see test_glib.c.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GlibTestConan(ConanFile):
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
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} -c './test_glib'", env="conanrun")
