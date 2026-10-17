from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class FdkAacTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "8"])

    def test(self):
        # 测试脚本分三阶段:探针 / 官方 fixture 套件(条件) / 合成 wav 烟测
        self.run(
            "sh %s %s %s"
            % (os.path.join(self.source_folder, "test.sh"),
               self.build_folder, self.source_folder),
            env="conanrun")
