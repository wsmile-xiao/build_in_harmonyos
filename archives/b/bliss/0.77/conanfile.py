#!/usr/bin/env python3
"""Conan recipe for bliss 0.77 — canonical labelings and automorphism
groups of graphs (C++, LGPL-2.1-or-later library / GPL-3.0 CLI).

bliss（Aalto 大学）计算图的自同构群与规范标号，纯 C++ 实现，无外部
运行时依赖（USE_GMP 可选，默认 OFF）。CMake 构建，产出：
- libbliss 库（lib/libbliss.so + include/bliss/*.hh + BlissConfig.cmake）
- bliss CLI（bin/bliss，图规范标号命令行工具）

OHOS 适配:
- CMake 无 Platform/HarmonyOS.cmake → 呈现为 Linux（CMAKE_SYSTEM_NAME
  Linux + CMAKE_CROSSCOMPILING=FALSE，鸿蒙 clang 驱动仍目标 aarch64）；
- 纯 C++ 无平台 API 依赖，无源码补丁；
- 测试: 运行 bliss CLI --canon 计算 Petersen 图规范标号 + test_package
  链接 libbliss 验证 C++ API。
"""
import textwrap

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class BlissConan(ConanFile):
    name = "bliss"
    version = "0.77"
    description = "Tool for computing automorphism groups and canonical labelings of graphs"
    license = "LGPL-2.1-or-later"
    homepage = "https://users.aalto.fi/~tjunttil/bliss/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 0001: 共享库符号可见性修复（上游 hidden 导致 CLI 无法链接 .so）
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)

        # 与 neovim-qt/qtquickeffectmaker 同款：CMake 无 Platform/HarmonyOS
        # 支持 → 呈现为 Linux 且置 CMAKE_CROSSCOMPILING=FALSE（鸿蒙 clang
        # 驱动仍目标 aarch64-linux-ohos，本机实际编译运行验证）。
        class OhosLinuxPlatformBlock(Block):
            template = textwrap.dedent(
                """\
                set(CMAKE_SYSTEM_NAME Linux)
                set(CMAKE_HOST_SYSTEM_NAME Linux)
                set(CMAKE_CROSSCOMPILING FALSE)
                set(CMAKE_SYSTEM_PROCESSOR aarch64)
                set(CMAKE_HOST_SYSTEM_PROCESSOR aarch64)
                """
            )

            def context(self):
                return {}

        tc.blocks["user_toolchain"] = OhosLinuxPlatformBlock
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["bliss"]
        self.cpp_info.set_property("cmake_file_name", "Bliss")
        self.cpp_info.set_property("cmake_target_name", "Bliss::libbliss")
