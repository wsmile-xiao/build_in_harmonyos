#!/usr/bin/env python3
"""Conan recipe — pybind11 3.1.0 (cmake, header-only)

上游 pybind/pybind11 v3.1.0，CMake 项目，产物为纯头文件库
（include/pybind11/*.h + cmake 配置）。无运行时第三方依赖。
R47 语言判定：pybind11 绑定包按边界规则判 cpp（SKILL R47 明确列出
"pybind11 绑定包判 cpp"；本任务 lang-preflight 误判 python 属已知
工具缺陷——绑定标记已命中但 cpp 占比 <70% 未触发绑定覆盖，见台账与
知识候选；交付物为 C++ 头文件库，pyproject.toml 仅承载可选 Python
打包，非主交付物）。

OHOS 适配要点：
- PYBIND11_NOPYTHON=ON：跳过 cmake 对 Python 头文件的搜索，配方构建
  阶段不依赖 Python 开发头；库本体仅安装头文件与 cmake 配置。
- test_package 消费侧编译需 Python.h（include/pybind11/detail/common.h
  经 conduit/wrap_include_python_h.h 无条件 #include <Python.h>），由
  test_package 注入宿主 Python include 目录（sysconfig），属测试环境
  便利，非包依赖。
- 无 requires/tool_requires：L0i 依赖 registry 解析为空 → 通过。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Pybind11Conan(ConanFile):
    name = "pybind11"
    version = "3.1.0"
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