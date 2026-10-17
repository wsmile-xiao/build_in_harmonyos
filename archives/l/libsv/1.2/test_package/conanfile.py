import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LibsvTestConan(ConanFile):
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
        # 真机/CI 为 OHOS 原生构建（非交叉）时执行完整运行验证；
        # 交叉构建环境只验证编译链接，跳过运行。
        if cross_building(self):
            self.output.info("Cross-building: skipping test run")
            return
        cmake = CMake(self)
        cmake.test()
        # 直接再跑一次二进制，满足 R34（实质 API 测试）证据要求；
        # conanrun 提供 LD_LIBRARY_PATH（共享库产物在 package 目录）。
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_sv"),
            env="conanrun",
        )
