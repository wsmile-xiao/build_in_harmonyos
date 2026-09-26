import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class JaulaTestConan(ConanFile):
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
        if not can_run(self):
            return
        # 三个消费者程序各自以断言计数决定退出码，任一非零即 test() 失败。
        for case_name in ("test_parse", "test_corpus", "test_errors"):
            cmd = os.path.join(self.cpp.build.bindir, case_name)
            self.run(cmd, env="conanrun")
