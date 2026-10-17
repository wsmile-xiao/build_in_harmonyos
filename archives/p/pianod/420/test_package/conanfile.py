#!/usr/bin/env python3
"""L1 consumer test for pianod2 (application package).

pianod2 installs executables only, so the consumer test drives the packaged
``pianod`` binary on two levels: link/introspection assertions plus a live
daemon handshake over the line protocol (R40 runtime evidence).  Both fail
loudly if a dependency is dropped or the service does not actually run.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Pianod2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        pkg = self.dependencies[self.tested_reference_str]
        tc = CMakeToolchain(self)
        # the daemon needs an explicit client dir; see test_package/CMakeLists.txt
        tc.variables["PIANOD_WWWDIR"] = os.path.join(pkg.package_folder, "share", "pianod", "html")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # packaged binary must be on PATH and report its version
        self.run("pianod -v", env="conanrun")
        # built consumer program: dependency introspection + live service check
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_pianod")
        self.run('"{}"'.format(test_bin), env="conanrun")
