import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KbdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 消费者只运行 kbd 交付的二进制（R34 行为断言），无需链接 kbd 库；
        # bin 路径由依赖图直接取包目录，绕开 target 接口。
        kbd = self.dependencies["kbd"]
        tc.variables["KBD_BIN_DIR"] = os.path.join(kbd.package_folder, "bin")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 12.38③: 直接执行消费者二进制，避免 ctest 包装层吞环境
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_kbd")
        self.run(f'"{bin_path}"', env="conanrun")
