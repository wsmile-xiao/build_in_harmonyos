import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building

from conan.errors import ConanInvalidConfiguration


class GraafTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake 不识别 OHOS 为目标平台，映射为 Linux/aarch64
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            qemu = os.environ.get("OHOS_QEMU", "")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run OHOS consumer tests"
                )
            self.run(f'"{qemu}" {os.path.join(self.cpp.build.bindirs[0], "test_package")}')
        else:
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"))
