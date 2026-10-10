from conan import ConanFile
import os

from conan.tools.cmake import CMake
from conan.tools.layout import basic_layout


class LibBtrfsDevTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv", "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        for executable in ("btrfs_consumer", "btrfs_ohos_abi"):
            path = os.path.join(self.build_folder, executable)
            self.run(f'"{path}"', env="conanrun")
