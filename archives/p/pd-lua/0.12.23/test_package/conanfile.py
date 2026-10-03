#!/usr/bin/env python3
"""test_package for pd-lua — Pd external (pdlua.pd_linux) smoke tests.

A Pd external can only run inside the Pd host (Pd supplies the API symbols
it links against), so the test drives the real `pd` binary from the
puredata dependency end-to-end (R34):
  1. `pd -lib pdlua` boots and reports the pdlua loader banner + Lua version.
  2. a `.pd_lua` external (hello) is instantiated through the loader and
     executes, proving the external API path works.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PdluaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
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
        pkg = self.dependencies["pd-lua"].package_folder
        pdlua_dir = os.path.join(pkg, "lib", "pd", "extra", "pdlua")
        pd_bin = os.path.join(
            self.dependencies["puredata"].package_folder, "bin", "pd"
        )
        test_pdlua = os.path.join(self.cpp.build.bindirs[0], "test_pdlua")
        self.run(f"{test_pdlua} {pd_bin} {pdlua_dir}", env="conanrun")
