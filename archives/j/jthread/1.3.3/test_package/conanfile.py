import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class JthreadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _find_compiler(self, name):
        candidates = [
            shutil.which(name),
            f"/data/service/hnp/bin/{name}",
            os.path.expanduser(f"~/usr/local/bin/{name}"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise RuntimeError(f"{name} compiler not found")

    def generate(self):
        cc = self._find_compiler("clang")
        cxx = self._find_compiler("clang++")
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_C_COMPILER"] = cc
        tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()

    def build(self):
        cc = self._find_compiler("clang")
        cxx = self._find_compiler("clang++")
        cmake = CMake(self)
        cmake.configure(
            variables={
                "CMAKE_C_COMPILER": cc,
                "CMAKE_CXX_COMPILER": cxx,
            }
        )
        cmake.build()

    def test(self):
        self.run(os.path.join(self.build_folder, "test_lifecycle"), env="conanrun")
        self.run(os.path.join(self.build_folder, "test_return_value"), env="conanrun")
        self.run(os.path.join(self.build_folder, "test_multiple_threads"), env="conanrun")
