import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class MyguiTestConan(ConanFile):
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
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # 真实运行被测包二进制（L0d 要求 test() 有 self.run()，非空壳）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_mygui"),
                 env="conanrun")
        # r11: headless 功能测试（Dummy 资源注册/DataManager API，无需显示）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_headless"),
                 env="conanrun")