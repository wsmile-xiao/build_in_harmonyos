import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibslaxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        cc = shutil.which("clang") or os.environ.get("CC") or "/data/service/hnp/bin/clang"
        cxx = shutil.which("clang++") or os.environ.get("CXX") or "/data/service/hnp/bin/clang++"
        tc.cache_variables["CMAKE_C_COMPILER"] = cc
        tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_package")
        self.run(exe, env="conanrun")
