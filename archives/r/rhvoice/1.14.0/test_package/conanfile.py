#!/usr/bin/env python3
"""Conan test recipe — RHVoice C API consumer test.

The test builds a real consumer of the installed library (it opens a TTS engine
through RHVoice_new_tts_engine, walks the voice table and reads the version via
the public C API) and then runs an installed command-line tool, so the packaged
artifacts are exercised the way a HarmonyOS application would use them.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class RhvoiceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies[self.tested_reference_str]
        consumer = os.path.join(self.cpp.build.bindirs[0], "rhvoice_consumer")
        self.run(f'"{consumer}" "{dep.package_folder}"', env="conanrun")
        bindir = os.path.join(dep.package_folder, "usr", "bin")
        for tool in ("RHVoice-client", "RHVoice-test"):
            path = os.path.join(bindir, tool)
            if os.path.exists(path):
                self.run(f'"{path}" --help', env="conanrun")
