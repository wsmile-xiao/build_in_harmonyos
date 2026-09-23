import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LFortranRuntimeTestConan(ConanFile):
    """test_package — 消费者视角：链接 lfortran-runtime 并真实调用其 C 运行时 API。"""
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # 直接执行测试二进制，作为 ctest 之外的独立运行证据
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_lfortran_runtime"), env="conanrun")
