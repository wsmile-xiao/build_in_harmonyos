import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class WxwidgetsGtk3TestConan(ConanFile):
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
        # R34: 实际执行被测包链接产物（无显示 API 验证，broadway 后端
        # 不需要显示连接即可运行）
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_wxgtk3")
        self.run(f'"{bin_path}"', env="conanrun")
