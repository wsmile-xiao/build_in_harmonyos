#!/usr/bin/env python3
"""Conan recipe — libkylin-ai-system-private 1.2.0.0 (header-only + 协议定义库).

Kylin AI 子系统私有库：ai-engine（C++17 INTERFACE 头库，AI 引擎抽象接口）+
ai-proto（gdbus/grpc 协议定义文件，无编译产物，仅供下游生成代码/消费）。
上游 debian/1.2.0.0 tag 无任何第三方依赖（Build-Depends 仅 cmake）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibKylinAiSystemPrivateConan(ConanFile):
    name = "libkylin-ai-system-private"
    version = "1.2.0.0"
    description = ("Kylin AI System Private Libs: AI engine plugin interfaces "
                   "(header-only) + gdbus/grpc protocol definitions")
    license = "GPL-3.0"
    homepage = "https://gitee.com/openkylin/libkylin-ai-system-private"
    url = "https://gitee.com/openkylin/libkylin-ai-system-private"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    exports_sources = "patches/*"

    def layout(self):
        cmake_layout(self)

    def source(self):
        # gitee 归档端点按 User-Agent 过滤：非 curl UA 返回 HTML 挑战页，
        # 显式传 curl UA 获取真实归档（内容与 tag debian/1.2.0.0 一致）。
        get(self, **self.conan_data["sources"]["1.2.0.0"],
            headers={"User-Agent": "curl/8.0"}, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # INTERFACE 库无编译产物，build 步骤仅生成安装清单
        cmake.build()
        cmake.install()

    def package_id(self):
        self.info.clear()          # header-only + 数据定义：单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # 两个上游 CMake 目标（INTERFACE）：ai-engine 头库 + ai-proto 协议定义
        self.cpp_info.components["aiengine"].set_property(
            "cmake_file_name", "KylinAiEngine")
        self.cpp_info.components["aiengine"].set_property(
            "cmake_target_name", "KylinAiEngine::KylinAiEngine")
        self.cpp_info.components["aiengine"].includedirs = ["include"]
        self.cpp_info.components["aiproto"].set_property(
            "cmake_file_name", "KylinAiProto")
        self.cpp_info.components["aiproto"].set_property(
            "cmake_target_name", "KylinAiProto::KylinAiProto")
        # 协议定义目录（gdbus XML / grpc proto），供下游生成代码
        self.cpp_info.components["aiproto"].resdirs = ["share/kylin-ai"]
