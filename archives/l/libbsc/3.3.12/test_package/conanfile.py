#!/usr/bin/env python3
"""test_package for libbsc 3.3.12 on HarmonyOS PC (aarch64).

Real verification (L0/test-quality rules):
- Library round-trip via a real consumer binary: bsc_init -> bsc_compress
  -> bsc_decompress -> memcmp byte-identical, on a synthetic corpus and
  real file data (/etc/profile).
- OHOS-specific checks: ELF64 AArch64 header, DT_SONAME present, no host
  paths baked into the .so, and a real CLI `bsc e`/`bsc d` round-trip
  (byte-identical) when the CLI is packaged — never just --help.
"""

import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class LibbscTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires("libbsc/3.3.12")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        # 1) real consumer round-trip (bsc_compress/bsc_decompress/memcmp)
        bin_dir = self.cpp.build.bindirs[0]
        self.run(f'"{os.path.join(bin_dir, "test_package")}"', env="conanrun")

        # 2) OHOS-specific: ELF64/AArch64, DT_SONAME, no host paths,
        #    real CLI round-trip (not --help)
        pkg_dir = self.dependencies["libbsc"].package_folder
        env = VirtualRunEnv(self).environment()
        env_vars = " ".join(f'{k}="{v}"' for k, v in env.vars(self).items())
        self.run(f'{env_vars} TEST_PACKAGE_DIR="{pkg_dir}" python3 "{self.source_folder}/ohos_checks.py"', env="conanrun")
