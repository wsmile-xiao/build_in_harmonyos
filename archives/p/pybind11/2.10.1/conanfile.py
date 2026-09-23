#!/usr/bin/env python3
"""Conan recipe — pybind11 2.10.1 (cmake, header-only)

上游 pybind/pybind11 v2.10.1，CMake 项目，产物为纯头文件库
（include/pybind11/*.h + cmake 配置）。无运行时第三方依赖。
R47 语言判定：pybind11 绑定包按边界规则判 cpp（其自身工具 lang_detect
D.4-2 亦注明 "pybind11 包装 C++ 库 → 判 cpp"）；仓库内 .py 文件为
tests/ 测试驱动与打包脚本，非主交付物。

OHOS 适配要点：
- PYBIND11_NOPYTHON=ON：跳过 cmake 对 Python 头文件的搜索，配方构建
  阶段不依赖 Python 开发头；库本体仅安装头文件与 cmake 配置。
- test_package 消费侧编译需 Python.h（pybind11/detail/common.h 无条件
  #include <Python.h>），由 test_package 注入宿主 Python include 目录
  （sysconfig），属测试环境便利，非包依赖。
- 无 requires/tool_requires：L0i 依赖 registry 解析为空 → 通过。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Pybind11Conan(ConanFile):
    name = "pybind11"
    version = "2.10.1"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # pybind11 本体为纯头文件 C++ 库，无运行时第三方依赖；
        # Python.h 仅为消费者按需引入，不构成包级依赖（L0i 解析为空）。
        pass

    def generate(self):
        tc = CMakeToolchain(self)
        # 与 fmt 12.2.0 同款 OHOS 守卫：conan 默认把 os=OHOS 映射为
        # CMAKE_SYSTEM_NAME=HarmonyOS，而 pybind11 cmake 不需平台宏，
        # 显式对齐 OHOS 以保持与平台文件一致。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 头文件库：不构建测试、不搜索 Python（配方阶段零 Python 依赖）
        tc.variables["PYBIND11_TEST"] = "OFF"
        tc.variables["PYBIND11_INSTALL"] = "ON"
        tc.variables["PYBIND11_NOPYTHON"] = "ON"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="")
        cmake.build()

    def package(self):
        CMake(self).install()

    def package_info(self):
        # header-only：仅包含目录，无链接库；导出 cmake 目标供 CMakeDeps 消费
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "pybind11")
        self.cpp_info.set_property("cmake_target_name", "pybind11::pybind11")