import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MpirTestConan(ConanFile):
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
        # R34：真实执行被测包产物并断言退出码。OHOS 上经 bash 包装执行二进制
        # （仓库惯例，/system/bin/sh 执行 ELF 不可靠）；conanrun 环境提供动态库路径。
        binary = os.path.join(self.cpp.build.bindirs[0], "test_mpir")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c {shlex.quote(binary)}", env="conanrun")
