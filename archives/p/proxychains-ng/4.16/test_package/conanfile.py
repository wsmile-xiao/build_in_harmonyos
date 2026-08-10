#!/usr/bin/env python3
"""Conan test_package — proxychains-ng 4.16.

L1 test: verifies that libproxychains4.so is linkable and the
exported function dalias_hash() returns a non-zero hash for non-empty input.

The library has a constructor that reads its config file on load.
We set PROXYCHAINS_CONF_FILE env var to point to the package's config
file so the library initializes correctly.

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ProxychainsNgTestConan(ConanFile):
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
        # libproxychains4.so has a constructor that reads the config file
        # on load. Set PROXYCHAINS_CONF_FILE to the package's config so
        # the library initializes correctly during the test.
        dep = self.dependencies["proxychains-ng"]
        config_path = os.path.join(dep.package_folder, "etc", "proxychains.conf")
        if os.path.exists(config_path):
            os.environ["PROXYCHAINS_CONF_FILE"] = config_path
        # Run the test executable directly
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_proxychains_ng")
        self.run(test_exe, env="conanrun")
