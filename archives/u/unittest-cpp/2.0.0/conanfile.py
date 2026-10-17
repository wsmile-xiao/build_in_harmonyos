#!/usr/bin/env python3
"""Conan recipe — unittest-cpp 2.0.0 (UnitTest++, C++ static test library, CMake).

上游测试集成（§10/R51）：CMake 主线自带
`add_custom_command(TARGET TestUnitTest++ POST_BUILD COMMAND TestUnitTest++)`，
`cmake --build` 阶段自动构建并**真实执行** 268 例上游套件（Release 下
`-DNDEBUG` 使 CrashingTestsAreReportedAsFailures 参与编译，验证
SignalTranslator=sigaction+siglongjmp 信号翻译在 OHOS/musl 生效）。
POST_BUILD 命令非零退出即构建失败 = 真实门禁，未用 ignore_errors。

-Wl,--code-sign（OHOS 工具链全局注入）× 上游 -Werror 的碰撞用官方开关
UTPP_AMPLIFY_WARNINGS=OFF 降级（conandata.yml 注释含首错逐字），零源码补丁。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class UnittestCppConan(ConanFile):
    name = "unittest-cpp"
    version = "2.0.0"
    description = ("UnitTest++ is a lightweight C++ unit test framework. "
                   "This package ships the static library plus its own test runner.")
    license = "MIT"
    homepage = "https://github.com/unittest-cpp/unittest-cpp"
    url = "https://github.com/unittest-cpp/unittest-cpp"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 cmake_minimum_required(VERSION 2.8.1)：CMake 4.x（平台 4.1.2）拒绝，
        # 官方开关经 cache_variables 注入（经验汇总 §1618）。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # OHOS 工具链全局注入 -Wl,--code-sign；上游 -Wall -Wextra -Werror 会把编译期
        # "linker argument unused" 告警升级成 error（实测首错见 notes.md 问题表）。
        # 用上游自带 option 降级警告强度，不改上游源码。
        tc.cache_variables["UTPP_AMPLIFY_WARNINGS"] = "OFF"
        # 上游默认把自身测试并入主构建（正是 §10 要求的真实执行入口），保持 ON。
        tc.cache_variables["UTPP_INCLUDE_TESTS_IN_BUILD"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # cmake.build() 内部即触发 POST_BUILD 执行 TestUnitTest++（268 例真实运行）；
        # 若测试失败则 POST_BUILD 非零退出，构建随之失败。
        cmake.build()
        # 独立复跑一次上游 runner 留数（ctest 未注册，runner 即上游测试入口本体；
        # TestResults 计数由二进制退出码表达：0=全过）。
        bin_path = os.path.join(self.build_folder,
                                *self.cpp.build.bindirs, "TestUnitTest++")
        if not os.path.isfile(bin_path):
            bin_path = os.path.join(self.build_folder, "TestUnitTest++")
        self.run(f'"{bin_path}"')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["UnitTest++"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "unittest-cpp")
        self.cpp_info.set_property("cmake_target_name", "unittest-cpp::unittest-cpp")
        self.cpp_info.set_property("pkg_config_name", "unittest-cpp")
