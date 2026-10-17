import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibabwTestConan(ConanFile):
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
        # 12.38③: ctest 包装层可能吃掉环境变量；直接执行消费者二进制，
        # 由 conanrun 环境提供聚合后的 LD_LIBRARY_PATH（libxml2 为共享库）。
        import os
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libabw")
        self.run(f'"{bin_path}"', env="conanrun")
