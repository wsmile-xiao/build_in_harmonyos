#!/usr/bin/env python3
"""Conan recipe for ns-3 3.48 (HarmonyOS PC adaptation).

ns-3 是离散事件网络仿真器（nsnam/ns-3-dev-git）。本配方裁剪至最小编译集：
core + network + point-to-point（NS3_ENABLED_MODULES，依赖闭包自动补全），
关闭全部可选 3rd-party 依赖（GTK3/GSL/SQLite/Eigen/libxml2）与 Python 绑定。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Ns3Conan(ConanFile):
    name = "ns-3"
    version = "3.48"
    description = (
        "ns-3 discrete-event network simulator (core/network/point-to-point "
        "minimal build for HarmonyOS PC)"
    )
    license = "GPL-2.0-only"
    homepage = "https://www.nsnam.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("network", "simulator", "discrete-event", "ns-3")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # ns-3 3.48 源码实际依赖 C++20（std::remove_cvref_t / std::bind_front），
        # 而 ohos-aarch64 profile 的 cppstd=17 不够。conan 的 cppstd block 会把
        # settings 的 17 写成普通变量（优先级高于 variables 的 CACHE 变量），
        # 因此必须先移除该 block，再经 variables 显式设置为 20。
        tc.blocks.remove("cppstd")
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_EXTENSIONS"] = "OFF"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # HarmonyOS 无 CMake Platform/HarmonyOS.cmake，CMAKE_SHARED_LIBRARY_SONAME_*_FLAG
        # 为空 → 共享库不带 DT_SONAME，DT_NEEDED 记录绝对构建路径
        # (.../b/build/lib/libns3.48-*.so)。消费者运行时会同时加载包内副本与构建
        # 目录副本，ns-3 的日志组件静态注册被重复执行 → NS_FATAL
        # ("Log component ... has already been registered once")。显式补 SONAME 标志，
        # 让 NEEDED 记录裸库名、由 LD_LIBRARY_PATH 唯一解析（E537 同类修复）。
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # ns-3 顶层要求 CMake >= 3.25（本机 4.1.2 满足）；ninja 已由 CMake 自动选择。
        # --- 编译目标最小化：只编 core/network/point-to-point ---
        tc.variables["NS3_ENABLED_MODULES"] = "core;network;point-to-point"
        tc.variables["NS3_EXAMPLES"] = "OFF"
        tc.variables["NS3_TESTS"] = "OFF"
        # --- 可选 3rd-party 依赖全部裁剪（QUIET 查找缺省自动禁用，不 FATAL）---
        tc.variables["NS3_GTK3"] = "OFF"
        tc.variables["NS3_GSL"] = "OFF"
        tc.variables["NS3_SQLITE"] = "OFF"
        tc.variables["NS3_EIGEN"] = "OFF"
        # --- Python 绑定关闭（不依赖 Python）---
        tc.variables["NS3_PYTHON_BINDINGS"] = "OFF"
        # --- 平台/工具链适配 ---
        tc.variables["NS3_VISUALIZER"] = "OFF"
        tc.variables["NS3_CCACHE"] = "OFF"
        # clang15 编译新代码警告面大，关闭 warnings-as-errors 防误炸
        tc.variables["NS3_WARNINGS_AS_ERRORS"] = "OFF"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 实测产物库名带 ns-3 版本号（libns3.48-<module>.so），cpp_info.libs
        # 必须与之一致，否则 CMakeDeps 报 "Library 'ns3-xxx' not found in package"。
        # 顺序按模块依赖：point-to-point -> network -> stats -> core。
        self.cpp_info.libs = [
            "ns3.48-point-to-point",
            "ns3.48-network",
            "ns3.48-stats",
            "ns3.48-core",
        ]
        self.cpp_info.set_property("cmake_file_name", "ns3")
        self.cpp_info.set_property("cmake_target_name", "ns3::core")