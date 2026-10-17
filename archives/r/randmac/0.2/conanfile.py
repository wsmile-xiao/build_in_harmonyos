#!/usr/bin/env python3
"""Conan recipe — randmac 0.2 (random MAC address generator, CMake).

VirtualSquare 单文件 C 工具：生成随机 MAC 地址（供 qemu/kvm 等虚拟机
启动参数使用）。构建产物为单个可执行文件 randmac（package_type =
application，R38 需软件级 commands.json）。

依赖 strcase/0.1（VirtualSquare 纯头文件多路分支库，本仓 PR #10505 适配）：
上游 CMakeLists.txt 用 check_include_file(strcase.h) 做存在性探测（缺失即
FATAL_ERROR），randmac.c 又 include <strcase.h> 并调用 strcase()/STRCASE()
宏。故通过 CMakeToolchain 同时注入 CMAKE_REQUIRED_INCLUDES（探测用）与
CMAKE_C_FLAGS -I（编译用）。

上游测试清点（R51）：上游无任何测试（无 test/ 目录、无 enable_testing/
add_test/CTestTestfile），N_static = 0；验证由 test_package 消费者测试承载
（真机运行 randmac 二进制，断言 MAC 格式与 OUI/strcase 行为）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class RandmacConan(ConanFile):
    name = "randmac"
    version = "0.2"
    description = "Generate random MAC addresses for VMs and scripts (VirtualSquare)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/virtualsquare/randmac"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R36 拓扑序：strcase/0.1 = 本仓 PR #10505（已提审）；其 release
        # 上传制品仓后本包 W0/CI 方可通过（本地验证用本地 create 的包）。
        self.requires("strcase/0.1")

    def validate(self):
        # R32: 平台判断用 in，不用 == "Linux"
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"randmac not validated for {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        strcase = self.dependencies["strcase"]
        incdir = os.path.join(strcase.package_folder,
                              strcase.cpp_info.includedirs[0])
        # R33：编译/探测标志全部经由 Toolchain 注入（release worker 上无
        # 裸 shell 环境变量）。-I 供 randmac.c 编译；CMAKE_REQUIRED_INCLUDES
        # 供上游 check_include_file(strcase.h) 探测，缺一处 configure 即 FATAL。
        tc.variables["CMAKE_C_FLAGS"] = f"-I{incdir}"
        tc.variables["CMAKE_REQUIRED_INCLUDES"] = incdir
        # §12.2/E077：cmake --install 字节级改写 RPATH 破坏链接期 .codesign，
        # musl 拒载。本包可执行文件无运行时 RPATH 需求（依赖仅 header-only），
        # 直接禁用 install RPATH 改写。
        tc.variables["CMAKE_SKIP_INSTALL_RPATH"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游无任何注册测试（见文件头清点），无可执行的上游测试套件；
        # 验证由 test_package 消费者测试承载。

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
