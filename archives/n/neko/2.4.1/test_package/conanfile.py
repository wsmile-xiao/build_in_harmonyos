#!/usr/bin/env python3
"""Consumer-side verification for Neko.

Builds test.c against the installed neko headers and libraries,
then runs the compiled test to verify Neko C API availability.
Also runs `neko -version` to confirm the command-line VM works.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class NekoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            dependency = self.dependencies["neko"]
            bindirs = dependency.cpp_info.bindirs
            libdirs = dependency.cpp_info.libdirs
            if not bindirs or not libdirs:
                raise ConanException(
                    "The neko package must declare non-empty bin and lib directories"
                )
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
            if not bash:
                raise ConanException("Neko runtime tests require bash on PATH")
            libdir = os.path.join(dependency.package_folder, libdirs[0])
            neko = os.path.join(
                dependency.package_folder,
                bindirs[0],
                "neko",
            )
            self.run(
                f'LD_LIBRARY_PATH="{libdir}" "{bash}" -c \'./test_neko\'',
                ignore_errors=False,
            )
            self.run(
                f'LD_LIBRARY_PATH="{libdir}" "{bash}" '
                f'-c \'"{neko}" -version\'',
                ignore_errors=False,
            )
