import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class NewlispTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # L0 stub_test_method 门禁要求 test() 显式调用 self.run 执行测试程序。
        # 先直接执行编译出的 C 冒烟测试（内部断言 (+ 1 2)→3、-v→10.7.5），
        # 再通过 ctest 运行 newlisp_arith / newlisp_version 直调断言。
        # newlisp 为静态单二进制，conanrun 环境提供其 bin 目录。
        test_bin = os.path.join(self.cpp.build.bindir, "test_newlisp")
        self.run('"{}"'.format(test_bin), env="conanrun")
        cmake = CMake(self)
        cmake.test()