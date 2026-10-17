#!/usr/bin/env python3
"""Conan recipe — CMake 项目（microservice-essentials 0.1.0）。

上游构建系统为 CMake（根 CMakeLists.txt：cmake_minimum_required 3.16.3,
C++17, src/ 库目标 + tests/ + examples/ 可选）。
本配方按官方源码构建静态库 microservice-essentials，不引入第三方依赖
（库本体零第三方依赖，测试/示例依赖仅由 BUILD_TESTING/BUILD_EXAMPLES 控制）。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class MicroserviceessentialsConan(ConanFile):
    name = "microservice-essentials"
    version = "0.1.0"
    description = "Portable C++ library for recurring concerns in microservice development"
    license = "MIT"
    homepage = "https://github.com/seboste/microservice-essentials"
    url = "https://github.com/seboste/microservice-essentials"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 库本体静态链接，系统同名库隔离（R26）
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 配方默认不构建上游测试/示例（依赖 catch2/nlohmann_json/cpp-httplib/grpc 等）
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
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
        self.cpp_info.libs = ["microservice-essentials"]
        if self.settings.os != "Windows":
            self.cpp_info.system_libs = ["pthread"]
