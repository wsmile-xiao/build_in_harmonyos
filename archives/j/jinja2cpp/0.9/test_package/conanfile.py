import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = 14
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.build_folder, "test_package")
            # OHOS 目标二进制依赖 SDK 的 libc++/libc++abi 运行时
            #（本机执行环境默认搜索路径不含 SDK llvm/lib）
            env = Environment()
            sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
            sdk_lib2 = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            if os.path.isdir(sdk_lib):
                env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
            if os.path.isdir(sdk_lib2):
                env.prepend_path("LD_LIBRARY_PATH", sdk_lib2)
            env.define("PATH", os.environ.get("PATH", ""))
            with env.vars(self).apply():
                self.run(cmd, env="conanrun")
