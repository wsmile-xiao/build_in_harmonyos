#!/usr/bin/env python3
"""Conan recipe template — Header-only / 无构建打包族（v12.21 新增）.

适用（普查 3,477 配方中占 26% 却长期无模板的族类）：
  A. Header-only C/C++ 库（doctest/catch2 型——cpp_info 仅头文件）
  B. 纯数据/文档/脚本重分发（字体/配置/资源包——无编译）
  C. 解释型脚本工具打包（perl/python/bash CLI 工具——只装不编）

用法: 替换 Gb/gb/0.8.7/gb 0.8.7/MIT/
     按变体删改 A/B/C 注释块。
铁律对齐: R34（test_package 必须真实调用被测物——header-only 也要写
test.c 实际 include 并使用接口，不能只 print）；R51（上游测试三步法
照常适用：header-only 库的上游测试也要清点+如实申报）。
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.cmake import cmake_layout


class GbConan(ConanFile):
    name = "gb"
    version = "0.8.7"
    description = "gb single-file public domain libraries for C & C++"
    license = "public-domain"
    homepage = "https://github.com/gingerBill/gb"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # header-only: 无编译阶段；补丁如有变更在此应用
        apply_conandata_patches(self)

    def package(self):
        # ── 变体 A: header-only 库 ──
        copy(self, "*.h", src=self.source_folder,
             dst=self.package_folder)
        copy(self, "*.hpp", src=self.source_folder,
             dst=self.package_folder)
        # 上游以 README.md 声明 public-domain 双许可（各头文件内含许可文本）
        copy(self, "README.md", src=self.source_folder,
             dst=self.package_folder, keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        # 变体 A: 标准头文件信息（头文件直接位于包根目录）
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["."]
