#!/usr/bin/env python3
"""Conan recipe — cpp-taskflow 3.8.0 (header-only C++17 task-graph library)

cpp-taskflow 是纯 header-only C++17 库（INTERFACE target，仅依赖 C++ 标准库
与 pthread），无第三方运行时依赖。上游 CMake 提供完整 install/export：
- install(DIRECTORY taskflow DESTINATION include)
- 导出 Taskflow::Taskflow 并安装 TaskflowConfig.cmake / ConfigVersion.cmake

适应要点：
- 关闭 TF_BUILD_TESTS / TF_BUILD_EXAMPLES（上游默认 ON）：conan create 只验证
  头文件安装与消费，不连带构建 28 个 unittests 与 examples（其依赖 3rd-party
  doctest/CLI11 等，仅上游自测用）。
- header-only：package_id 与编译器/架构无关（self.info.clear()）。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class CppTaskflowConan(ConanFile):
    name = "cpp-taskflow"
    version = "3.8.0"
    package_type = "header-library"
    license = "MIT"
    homepage = "https://github.com/taskflow/taskflow"
    url = "https://github.com/taskflow/taskflow"
    description = "A General-purpose Parallel and Heterogeneous Task Programming System"
    topics = ("taskflow", "tasking", "parallel", "heterogeneous", "c++17")
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        cmake_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # Header-only: package ID independent of compiler/build_type/arch
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游默认 TF_BUILD_TESTS=ON / TF_BUILD_EXAMPLES=ON：配包装插时关掉，
        # 仅安装头文件 + CMake config（26 个 unittests 由本任务单独验证）
        tc.variables["TF_BUILD_TESTS"] = "OFF"
        tc.variables["TF_BUILD_EXAMPLES"] = "OFF"
        tc.variables["TF_BUILD_BENCHMARKS"] = "OFF"
        tc.variables["TF_BUILD_PROFILER"] = "OFF"
        tc.variables["TF_BUILD_CUDA"] = "OFF"
        tc.variables["TF_BUILD_SYCL"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Taskflow")
        self.cpp_info.set_property("cmake_target_name", "Taskflow::Taskflow")
        # header-only：无可链接库
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = ["include"]