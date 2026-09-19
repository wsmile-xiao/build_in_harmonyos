import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeToolchain, CMakeDeps
from conan.tools.build import can_run


class TestOnnxruntime(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # ONNX Runtime 1.29.1 requires C++20 (onnxruntime_language_standard_versions.cmake).
        self.settings.compiler.cppstd = "20"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.cpp.build.bindirs[0], "test_onnxruntime")
            self.run(test_bin, env="conanrun")
