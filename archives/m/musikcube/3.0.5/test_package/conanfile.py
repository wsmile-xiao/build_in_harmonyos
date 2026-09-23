import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MusikcubeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["MUSIKCUBE_TEST_PACKAGE"] = True
        tc.generate()

    def build(self):
        CMake(self).configure()
        CMake(self).build()

    def test(self):
        # CI L0d 门禁要求 test() 内显式 self.run() 执行测试程序；
        # ELF 由 build() 阶段 CMake 产出，OHOS aarch64 环境可直接运行；
        # conanrun 环境提供依赖共享库（curl/ffmpeg/taglib 等）的 LD_LIBRARY_PATH
        exe = os.path.join(self.build_folder, "musikcube_core_test")
        self.run(f'"{exe}"', env="conanrun")
