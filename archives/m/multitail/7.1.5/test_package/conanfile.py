#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.cmake import CMake


class MultitailTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # conanrun 环境包含 multitail 的 bin 目录
        test_bin = os.path.join(self.build_folder, "test_multitail")
        # multitail 安装到 usr/local/bin（CMake 默认 prefix /usr/local），
        # 传完整路径给 test_multitail（不依赖 PATH——CI #18573 实测 exit 32512）
        mt_bin = os.path.join(self.dependencies["multitail"].package_folder,
                              "usr", "local", "bin", "multitail")
        self.run(f'"{test_bin}" "{mt_bin}"', env="conanrun")
