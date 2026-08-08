#!/usr/bin/env python3
"""Installed CLI and static-library consumers for Poly/ML."""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PolymlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Conan resolves the special test-package value "$TMP" with
        # tempfile.mkdtemp(), respecting TMPDIR and creating a unique
        # out-of-source build/generators root for each invocation.
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # CMakeUserPresets.json is normally emitted next to CMakeLists.txt;
        # disable it so generation remains entirely in generators_folder.
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("交叉构建场景不运行目标程序")
            return
        self.run(os.path.join(self.build_folder, "polyml_static_consumer"),
                 env="conanrun")
        poly = os.path.join(self.dependencies["polyml"].package_folder,
                            "bin", "poly")
        script = os.path.join(self.source_folder, "test_polyml.ML")
        wrapper = os.path.join(self.source_folder, "test_polyml.sh")
        self.run(f'/usr/bin/sh "{wrapper}" "{poly}" "{script}"',
                 env="conanrun")
