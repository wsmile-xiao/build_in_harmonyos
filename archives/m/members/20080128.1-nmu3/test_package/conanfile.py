#!/usr/bin/env python3
"""test_package for members — 鸿蒙特有消费者用例（rule12）。

流程：Conan 通过 OHOS profile 消费被测包 members（取其安装的 bin/members）→
用 OHOS 工具链（musl）编译消费者程序 test_members.cpp → 运行它；消费者再把
members 当被测对象拉起，用同一个 libc 的 getgrgid/getgrnam/getpwent 独立算出
期望输出并逐项比对（选项解析、退出码、stderr、主/附属组成员）。

消费者是 aarch64-linux-ohos 的产物：构建主机不是 aarch64 时（如 x86 runner）
无法原生执行，此时只完成编译链接并明确提示「未运行」，不把它当作已通过；
在 aarch64（OHOS PC / CI worker）上则必须运行且全部断言通过。
"""
import os
import platform

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MembersTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        members = os.path.join(
            self.dependencies["members"].package_folder, "bin", "members")
        assert os.path.isfile(members), f"members binary not found: {members}"
        consumer = os.path.join(self.build_folder, "test_members")
        assert os.path.isfile(consumer), f"consumer not built: {consumer}"

        if platform.machine().lower() not in ("aarch64", "arm64"):
            self.output.warning(
                "host is %s: aarch64-linux-ohos consumer compiled and linked "
                "but NOT executed here (run by CI on aarch64)"
                % platform.machine())
            return
        self.run(f'"{consumer}" "{members}"', env="conanrun")
