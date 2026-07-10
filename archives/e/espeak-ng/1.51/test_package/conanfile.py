import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class EspeakngTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        clang = "/storage/Users/currentUser/.harmonybrew/bin/clang"
        clangxx = "/storage/Users/currentUser/.harmonybrew/bin/clang++"
        if os.path.exists(clang):
            tc.variables["CMAKE_C_COMPILER"] = clang
        if os.path.exists(clangxx):
            tc.variables["CMAKE_CXX_COMPILER"] = clangxx
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindir, "test_espeak_ng")
        # Set LD_LIBRARY_PATH to find libespeak-ng.so
        lib_dir = os.path.join(self.dependencies["espeak-ng"].package_folder, "lib")
        self.run(f"LD_LIBRARY_PATH={lib_dir} {test_bin}", env="conanrun")
