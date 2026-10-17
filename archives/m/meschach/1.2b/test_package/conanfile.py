from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class MeschachTestConan(ConanFile):
    """test_package for meschach — 消费已安装的静态库跑真实 API 断言。"""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("./meschach_test", env="conanrun")
