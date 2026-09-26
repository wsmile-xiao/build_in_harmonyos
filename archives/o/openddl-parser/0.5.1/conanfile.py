#!/usr/bin/env python3
"""Conan recipe — openddl-parser 0.5.1 (CMake C++11 OpenDDL parser 库)."""

import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)

required_conan_version = ">=2.0"


class OpenddlparserConan(ConanFile):
    name = "openddl-parser"
    version = "0.5.1"
    description = "A simple and fast OpenDDL Parser"
    license = "MIT"
    homepage = "https://github.com/kimkulling/openddl-parser"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("openddl", "parser")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游 0 依赖（W0: ci/scripts/preflight_check.sh 实测「无依赖需要检查」）
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        shared = self.options.shared == True  # noqa: E712 —— OptionValue 与 True 显式比较
        tc = CMakeToolchain(self)
        # 上游语义: DDL_STATIC_LIBRARY=ON ⇒ DDL_BUILD_SHARED_LIBS 默认 OFF（静态）。
        tc.variables["DDL_STATIC_LIBRARY"] = not shared
        tc.variables["DDL_BUILD_SHARED_LIBS"] = shared
        # 上游单元测试（contrib/gtest-1.7.0 内嵌 gtest + test/ 目录）在 build() 内运行，
        # 与仓库 gtest 消费先例一致：内嵌 gtest 直接编进 unittest 目标，不引入 conan gtest 依赖。
        tc.variables["DDL_BUILD_TESTS"] = True
        tc.variables["DDL_BUILD_PARSER_DEMO"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试（TEST_QUALITY_SPEC §3.1：build() 内跑上游测试）──
        # 上游 CMake 不注册 CTest 用例，直接运行 gtest 可执行文件；
        # 结果（125 个 TEST/TEST_F）同时记入 reports/test-report.md 与 PR 正文。
        self.run(os.path.join("bin", "openddlparser_unittest"))

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # 上游 install(EXPORT) 的 openddlparser-config.cmake 交由 CMakeDeps 接管，
        # 避免 find_package 出现两份配置（与 CCI 同口径）。
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "openddlparser")
        self.cpp_info.set_property("cmake_target_name", "openddlparser::openddlparser")
        self.cpp_info.libs = ["openddlparser"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
        if not self.options.shared:
            self.cpp_info.defines.append("OPENDDL_STATIC_LIBARY")
