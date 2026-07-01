import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        libs = self.dependencies["glfw"].cpp_info.libs
        target_lib = libs[0] if libs else "glfw"
        cmake.configure(variables={"TARGET_LIB": target_lib})
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: 产物为 ohos_aarch64，本机不可运行，只验编译+链接")
            return
        cmd = os.path.join(self.cpp.build.bindir, "test_glfw")
        self.run(cmd, env="conanrun")
