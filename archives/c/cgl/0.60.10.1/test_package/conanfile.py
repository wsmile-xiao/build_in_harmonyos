import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CglTestConan(ConanFile):
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
            self.run(
                os.path.join(self.build_folder, "test_cgl"),
                env="conanrun",
            )
            # HarmonyOS special test and consumer use case (public CglLandP API)
            self.run(
                os.path.join(self.build_folder, "landp_ohos_test"),
                env="conanrun",
            )
            self.run(
                os.path.join(self.build_folder, "landp_consumer"),
                env="conanrun",
            )
