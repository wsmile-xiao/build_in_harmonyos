#!/usr/bin/env python3
"""test_package for libobjfwhid1 — compiles an Objective-C consumer that
genuinely calls the ObjFWHID public API (OHGameController) and links
libobjfwhid / libobjfw / libobjfwrt (R34: no empty-shell tests)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libobjfwhid1TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # E074: 本机 HMDFS 上 make -jN 的 jobserver mkfifo（TMPDIR）会
        # "Operation not permitted"，serialize 构建（cmake --build -- -j1）。
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        bindir = os.path.join(self.cpp.build.bindirs[0], "")
        # Objective-C consumer: genuinely calls +[OHGameController controllers].
        bin_oc = os.path.join(bindir, "test_libobjfwhid1")
        self.run(bin_oc, env="conanrun")
        # Plain C consumer: verifies libobjfwrt links and ObjFW classes register.
        bin_c = os.path.join(bindir, "test_runtime")
        self.run(bin_c, env="conanrun")
