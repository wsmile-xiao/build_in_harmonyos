import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def configure(self):
        # 与主配方一致：移除 os.version 依赖，避免 OHOS 下包 Invalid
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_dir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bin_dir, "test_hash_consumer"), env="conanrun")
        self.run(os.path.join(bin_dir, "hash_ohos_test"), env="conanrun")