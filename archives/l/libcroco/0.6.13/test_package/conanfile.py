from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libcroco 公共头（cr-utils.h）直接 #include <glib.h>，真实消费者
        # 必然同时链接 glib/libxml2。显式声明为直接依赖使 CMakeDeps 为
        # 它们生成完整（非空 include）的 data 文件——作为传递依赖时
        # include 目录不会被归一化为绝对路径（AbiWord 插件配方同一坑）。
        self.requires("glib/2.88.0.1")
        self.requires("libxml2/2.15.3.1")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "consumer")
            self.run(bin_path, env="conanrun")
