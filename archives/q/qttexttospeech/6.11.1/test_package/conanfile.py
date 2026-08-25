import os
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
            "Qt6TextToSpeech_LIB_DIR": self.dependencies["qttexttospeech"].package_folder + "/lib",
            "Qt6Core_LIB_DIR": self.dependencies["qtbase"].package_folder + "/lib",
            "Qt6_INCLUDE_DIR": self.dependencies["qtbase"].package_folder + "/include",
            "Qt6TextToSpeech_INCLUDE_DIR": self.dependencies["qttexttospeech"].package_folder + "/include",
        })
        cmake.build()

    def test(self):
        # 鸿蒙 musl namespace 无法加载自定义 Qt .so（libQt6TextToSpeech/libQt6Core）——
        # 编译链接已由 CMake build 验证；此处以产物完整性验证 + self.run 代替运行。
        pkg = self.dependencies["qttexttospeech"].package_folder
        assert os.path.exists(os.path.join(pkg, "lib", "libQt6TextToSpeech.so")), "缺少 libQt6TextToSpeech.so"
        self.run("ls -la %s/lib/libQt6TextToSpeech.so" % pkg)
        self.output.info("qttexttospeech 产物验证通过: libQt6TextToSpeech.so")
