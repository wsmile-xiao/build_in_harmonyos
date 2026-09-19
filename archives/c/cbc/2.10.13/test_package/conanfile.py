import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CbcTestConan(ConanFile):
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
        if can_run(self):
            CMake(self).test()
            # 消费者冒烟测试（Cbc C 接口求解 0-1 背包）
            self.run(
                os.path.join(self.build_folder, "test_cbc"),
                env="conanrun",
            )
            # HarmonyOS 专项测试（Cbc C 接口建模求解并断言最优值）
            self.run(
                os.path.join(self.build_folder, "cbc_ohos_test"),
                env="conanrun",
            )
            # 消费者用例（仅使用已安装公开头/库读取 MPS 并求解）
            self.run(
                os.path.join(self.build_folder, "cbc_consumer"),
                env="conanrun",
            )