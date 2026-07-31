#!/usr/bin/env python3
"""Conan test_package for Carla — verifies carla binaries run correctly.

Carla's `make install` produces:
  - bin/carla-single    : Python launcher script
  - lib/carla/libcarla_*  : backend shared libraries
  - lib/carla/carla-bridge-* : plugin bridge binaries
  - lib/carla/carla-discovery-* : plugin discovery binaries
  - lib/carla_utils.so  : utility library

The test runs test_carla.sh which verifies:
  1. carla-discovery-native binary exists and runs
  2. carla-discovery-native prints a usage line (live ELF reached main)
  3. libcarla_utils.so exists in lib/carla/
"""
import os
from conan import ConanFile


class CarlaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["carla"].package_folder
        test_script = os.path.join(self.source_folder, "test_carla.sh")
        # self.run() is required by CI L0d gate (R34: test must
        # substantively depend on the tested package).
        self.run(f'sh "{test_script}" "{pkg_folder}"', env="conanrun")
