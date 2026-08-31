#!/usr/bin/env python3
"""Conan test_package — execstack 20130503

Tests the execstack CLI tool by building a C test program that
invokes the execstack binary via popen() to verify it runs correctly.
execstack is a CLI application (not a library), so we test by running
the binary itself.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ExecstackTestConan(ConanFile):
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
        # Find the execstack binary in the dependency's package folder
        # In Conan 2, self.dependencies.values() gives ConanDependency objects
        execstack_bin = None
        for dep in self.dependencies.values():
            candidate = os.path.join(dep.package_folder, "bin", "execstack")
            if os.path.isfile(candidate):
                execstack_bin = candidate
                break
        if not execstack_bin:
            self.output.error("execstack binary not found in dependencies")
            return
        # execstack is dynamically linked against libelf.so (from elfutils).
        # VirtualRunEnv (conanrun) sets LD_LIBRARY_PATH so the binary can
        # find its shared library deps at runtime. EXECSTACK_BIN is passed
        # via os.environ so the test program (and its popen child) inherit it.
        os.environ["EXECSTACK_BIN"] = execstack_bin
        test_bin = os.path.join(self.build_folder, "test_execstack")
        self.run(test_bin, env="conanrun")
