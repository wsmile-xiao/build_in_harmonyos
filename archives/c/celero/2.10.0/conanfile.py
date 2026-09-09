#!/usr/bin/env python3
"""Conan recipe for celero 2.10.0 — C++ micro-benchmarking library.

Celero is a feature-rich micro-benchmarking framework for C++, built on
modern C++ and pthreads. Build system: CMake 3.16+. Library itself has
zero external dependencies; upstream GTest unit tests (67 cases) are
enabled via test_requires gtest and executed during build().

License: Apache-2.0.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CeleroConan(ConanFile):
    name = "celero"
    version = "2.10.0"
    description = "Celero is a C++ micro-benchmarking library to measure the performance of C++ code"
    license = "Apache-2.0"
    homepage = "https://github.com/DigitalInBlue/Celero"
    url = "https://github.com/DigitalInBlue/Celero"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # 仅上游单测使用，不传播给消费者
    test_requires = "gtest/1.17.0.1"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"celero {self.version} only supports Linux and OHOS, "
                f"got os={self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 基于 Linux 内核，CMake 不认识 OHOS 平台 → 显式声明为 Linux
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        arch = str(self.settings.arch)
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = (
            "aarch64" if arch.startswith("armv8") else arch
        )
        # 静态/动态与 PIC 由 Conan 选项驱动
        tc.variables["CELERO_COMPILE_DYNAMIC_LIBRARIES"] = bool(
            self.options.shared
        )
        tc.variables["CELERO_COMPILE_PIC"] = bool(self.options.get_safe("fPIC", True))
        # 关闭所有可选功能，只构建核心库与上游单测
        tc.variables["CELERO_ENABLE_EXPERIMENTS"] = False   # 示例程序
        tc.variables["CELERO_ENABLE_TESTS"] = True          # 上游 GTest 测试（67 用例）
        # AUTO_RUN 会在 POST_BUILD 自动跑测试且行为不可控，改为 build() 显式执行
        tc.variables["CELERO_ENABLE_AUTO_RUN_TESTS"] = False
        tc.variables["CELERO_ENABLE_FOLDERS"] = False
        # 交叉编译下 -Werror 风险高（交叉 clang 警告与本地不同），关闭
        tc.variables["CELERO_ENABLE_WARNINGS_AS_ERRORS"] = False
        tc.variables["CELERO_ENABLE_CLANG_TIDY_CHECKS"] = False
        tc.variables["CELERO_ENABLE_CLANG_ADDRESS_SANITIZER"] = False
        # Debug 构建默认给 lib 加 "-d" 后缀，清掉以保证库名稳定
        tc.variables["CMAKE_DEBUG_POSTFIX"] = ""
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not self.conf.get("tools.build:skip_test", default=False):
            # 上游 GTest 单测：直接执行 celero-test（AUTO_RUN 关闭时未注册 ctest）
            exe = os.path.join(self.build_folder, "celero-test")
            if not os.path.isfile(exe):
                exe = os.path.join(
                    self.build_folder, str(self.settings.build_type), "celero-test"
                )
            self.run(f'"{exe}"', env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "license.txt",
             dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["celero"]
        # 上游 CMake config 无命名空间，target 名就是 celero
        self.cpp_info.set_property("cmake_target_name", "celero")
        self.cpp_info.set_property("cmake_file_name", "celero")
        self.cpp_info.set_property("pkg_config_name", "celero")
        if not self.options.shared:
            self.cpp_info.defines = ["CELERO_STATIC"]
        # POSIX 上 std::thread 需要 pthread
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
