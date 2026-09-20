#!/usr/bin/env python3
"""Consumer test for taocpp-tuple 1.0.0 (header-only C++11 tuple library).

L1 官方测试（R34）：必须实质调用被测包 API。本测试 include
<tao/tuple/tuple.hpp> 并通过 tao::tuple / tao::make_tuple / tao::tie /
tao::tuple_cat / 按类型 get<> 构造、读取、比较与拼接，验证消费者
（业务上层组件）仅凭已安装公开头文件即可编译、链接并正确运行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TaocppTupleTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def configure(self):
        self.settings.rm_safe("os.version")

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.15"
        tc.generate()

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        # 消费者测试（R34：实质调用公开 API）
        self.run(os.path.join(bindir, "test_taocpp_tuple"), env="conanrun")
        # HarmonyOS 专项测试（OHOS 工具链真实运行）
        self.run(os.path.join(bindir, "test_ohos"), env="conanrun")
