import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class AuTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def configure(self):
        # 与主配方一致: OHOS 下 settings.os.version 由 OHOS 适配 conan
        # 处理, 测试包无需其值, 移除避免 Invalid ID。
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 与主配方一致: OHOS clang 使用 libc++, 避免注入 -stdlib=libstdc++。
        tc.cache_variables["CMAKE_CXX_FLAGS"] = "-stdlib=libc++"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_au")
        self.run(test_bin, env="conanrun")