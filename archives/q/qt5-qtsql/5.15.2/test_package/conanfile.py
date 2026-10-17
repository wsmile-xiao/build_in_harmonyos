"""验证安装后的 QtSql 包可以被独立 CMake 消费者使用。"""

import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class QtSqlConsumer(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        """仅直接依赖被测包，验证它完整导出了依赖关系。"""
        self.requires(self.tested_reference_str)

    def layout(self):
        """使用标准 CMake 构建目录布局。"""
        cmake_layout(self)

    def generate(self):
        """通过 Conan 生成 CMake 依赖目标和工具链。"""
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()
        CMakeToolchain(self, generator="Ninja").generate()

    def build(self):
        """编译真实调用 QtSql API 的消费者。"""
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        """在包提供的运行环境中验证 SQLite 插件和数据库行为。"""
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_qtsql"), env="conanrun")
