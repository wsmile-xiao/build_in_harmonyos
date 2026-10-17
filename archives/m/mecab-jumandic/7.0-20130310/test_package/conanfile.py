#!/usr/bin/env python3
"""test_package for mecab-jumandic 7.0-20130310.

Two-tier consumer test:
1. Data integrity (test_mecab_jumandic.py via self.run, CI L0d gate):
   file existence, counts, UTF-8 quirks, entry counts, binary indices.
2. HarmonyOS-specific target-environment consumption: compile and run a
   native C++ consumer against libmecab (mecab/0.996) that loads THIS
   package's binary dictionary and performs Japanese morphological analysis
   on fixed samples with exact golden-output comparison.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MecabJumandicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libmecab is required to consume the dictionary on the target env.
        self.requires("mecab/0.996")

    def layout(self):
        cmake_layout(self)

    def build(self):
        CMake(self).configure()
        CMake(self).build()

    def test(self):
        # 1. Data integrity test (standalone script)
        dep = self.dependencies["mecab-jumandic"]
        dic_dir = os.path.join(dep.package_folder, "dic")
        self.run(f'python3 {self.source_folder}/test_mecab_jumandic.py "{dic_dir}"',
                 cwd=self.source_folder, env="conanrun")

        # 2. HarmonyOS target-environment consumption test (native binary)
        exe = os.path.join(self.cpp.build.bindirs[0], "test_package")
        self.run(f'"{exe}" "{dic_dir}"', env="conanrun")
