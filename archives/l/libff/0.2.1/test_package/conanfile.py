#!/usr/bin/env python3
"""test_package — libff 0.2.1 消费者视角验证

编译并运行 test_package.cpp（消费者 1/1：ALT_BN128 配对、群运算、
域运算、序列化往返；17 项显式 CHECK 验证 bilinearity 等数学不变量，
不依赖 assert/NDEBUG，Release 构建下同样真实执行）与
test_package_ohos.cpp（鸿蒙专项 1/1：NO_PROCPS 回退、aarch64 可移植
路径、常数一致性、配对确定性、包内 libff.a 对象级检查）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires("libff/0.2.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # 对象级检查需要**包内** libff.a 的绝对路径。CMakeDeps 生成的
        # libff::ff 是 INTERFACE IMPORTED 包装目标（不含 IMPORTED_LOCATION，
        # $<TARGET_FILE> 不可用），故由配方侧解析 conan 缓存包目录注入。
        libff = self.dependencies["libff"]
        archive = os.path.join(libff.package_folder, "lib", "libff.a")
        if not os.path.isfile(archive):
            raise FileNotFoundError(f"libff static archive not found: {archive}")
        cmake.configure(variables={"LIBFF_ARCHIVE_PATH": archive})
        cmake.build()

    def test(self):
        if can_run(self):
            # 真实运行：输出 + 断言
            self.run(f'ctest --test-dir "{self.build_folder}" --output-on-failure', env="conanrun")
        else:
            # 交叉编译：构建本身就是消费者验证（编译 + 链接成功）
            # test_package 二进制不本机运行，但 cmake.build() 已验证链接完整性
            self.output.info(
                "Cross-compiling for OHOS: test_package binary built and linked "
                "against libff (run on target: ctest)"
            )
