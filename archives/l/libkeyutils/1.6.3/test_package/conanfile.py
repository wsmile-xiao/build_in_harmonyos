#!/usr/bin/env python3
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibkeyutilsTestConan(ConanFile):
    settings = ("os", "compiler", "build_type", "arch")
    generators = ("CMakeDeps", "CMakeToolchain")
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: self.run() required by CI L0d gate; must call the real binary.
        self.run("./test_keyutils", env="conanrun")
