import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import save


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    # CMakeToolchain 在 generate() 中定制实例化（OHOS 平台守卫），
    # 因此不放进 generators 属性，避免重复声明报错。
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 适配：与 recipe 同理，把 CMAKE_SYSTEM_NAME 指回 OHOS。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: 只验编译+链接")
            return
        bin_path = os.path.join(self.cpp.build.bindir, "test_package")
        self.run(bin_path, env="conanrun")