from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # Qt6Config.cmake 由 Qt 自行安装于 lib/cmake/Qt6/（cmake_find_mode=none），
        # CMakeDeps 不生成——显式传 Qt6_DIR 供 find_package(Qt6) 定位。
        cmake.configure(variables={
            "Qt6_DIR": self.dependencies["qtbase-sql-dbus"].package_folder + "/lib/cmake/Qt6",
        })
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d 门禁要求 test() 包含 self.run() 调用（stub_test_method 检测）
        self.run("ls -la %s" % self.build_folder)
