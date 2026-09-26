#!/usr/bin/env python3
"""Conan recipe for parg 1.0.3 — portable argv parser library in C.

Upstream is a two-file library (parg.c/parg.h) built with CMake. The upstream
CMakeLists.txt defines no install() rules, so package() copies the artifacts
explicitly (headers / library / license). Upstream tests use the greatest
single-header framework, registered with CTest as `test_parg`
(32 cases / 196 assertions) and are executed in build() via ctest.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class PargConan(ConanFile):
    name = "parg"
    version = "1.0.3"
    description = "Portable argv parser library in C, modeled on getopt/getopt_long"
    license = "MIT-0"
    homepage = "https://github.com/jibsen/parg"
    url = "https://github.com/jibsen/parg"
    topics = ("argument-parsing", "getopt", "argv", "c")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 零运行依赖（W0 已核：上游 CMakeLists 无任何 find_package/外部链接）
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 add_library(parg parg.c parg.h) 未指定类型，由 BUILD_SHARED_LIBS 决定
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            # 上游 greatest 套件经 CTest 执行（ctest 注册名 test_parg）
            cmake.test()
            # 再直跑一次，把 greatest 汇总行（用例数/断言数）打进 conan create 日志，
            # 供 PR 正文计数从设备日志取数（ctest 汇总只显示注册条目数 1）
            self.run(os.path.join(self.build_folder, "test_parg"))

    def package(self):
        copy(
            self,
            "parg.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        # 上游无 install() 规则，产物（libparg.a / libparg.so）按构建树就地打包
        copy(
            self,
            "libparg*",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["parg"]
        self.cpp_info.set_property("cmake_file_name", "parg")
        self.cpp_info.set_property("cmake_target_name", "parg::parg")
        self.cpp_info.set_property("pkg_config_name", "parg")
