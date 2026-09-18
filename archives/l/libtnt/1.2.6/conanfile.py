#!/usr/bin/env python3
"""Conan recipe — libtnt 1.2.6 (Template Numerical Toolkit, NIST).

TNT（Template Numerical Toolkit）是 NIST 开发的 C++ 科学计算数值模板库
（https://math.nist.gov/tnt/），Debian 发行版打包名 libtnt。1.2.6 为官方
最终发布版（NIST 站点此后仅维护性再分发），零依赖纯 header 交付：
21 个 .h 头文件（Array1D/2D/3D、Fortran_Array1D/2D/3D、
Sparse_Matrix_CompRow(CSR 视图)、Stopwatch、Vector/Matrix(deprecated
pre-1.0 API)、tnt.h 聚合头等）。

形态选型（参照 compile-time-regular 3.11.0 与 v12.21 headeronly 模板）：
- package_type = "header-library"，无任何编译产物；
- 官方 zip 为扁平结构（无顶层目录、无构建系统、无 LICENSE 独立文件），
  NIST 公共领域声明内嵌于每个头文件头部注释，package() 从 tnt.h 提取
  该声明块落盘为 licenses/LICENSE；
- 上游 1.2.6 无测试套件（R51 清点证据见 notes.md 与
  test_package/MANIFEST.yml），消费者 API 验证由 test_package 运行期
  数值断言承担（Array1D/2D/3D、Fortran 1-based、CSR、Stopwatch）；
- 许可证：title 17 U.S.C. §105 公共领域（SPDX: NIST-PD）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.layout import basic_layout


class LibTntConan(ConanFile):
    name = "libtnt"
    version = "1.2.6"
    description = "Template Numerical Toolkit (TNT) — numerical arrays and matrix interfaces for scientific computing in C++ (NIST)"
    license = "NIST-PD"
    homepage = "https://math.nist.gov/tnt/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    # header-only：settings 声明但 binary 由 header-only 模式归一
    settings = "os", "compiler", "build_type", "arch"

    # 上游 no_copy_source：源码只读，package 阶段直接从 source_folder 拷贝
    no_copy_source = True

    def export_sources(self):
        # 补丁文件（0001：Sparse_Matrix_CompRow 构造函数 const 修复）
        # 进入 recipe 导出源，改补丁时 recipe revision 自动更新
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # 官方 zip 为扁平结构（21 个 .h 位于压缩包根，无顶层目录），
        # 必须 strip_root=False：Conan 2 的 zip 剥根实现会把扁平条目的
        # 公共字符串前缀（"tnt"）误判为根目录，随后 name.split("/", 1)[1]
        # 直接 IndexError（本机 conan 2.31.2 实测复现）
        get(self, **self.conan_data["sources"], strip_root=False)
        # tnt.h 在 clang 下 include 即编译失败的上游硬缺陷修复
        # （详见 patches/0001 与 notes.md）
        apply_conandata_patches(self)

    # 无编译阶段：header-only，不定义 build()（R34 的 API 验证在 test_package）

    def package(self):
        # 头文件全量（扁平 include/tnt*.h，与上游布局一致）
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        # 上游 zip 无独立 LICENSE 文件：NIST 公共领域声明内嵌于每个头
        # 文件头部统一注释块，此处从 tnt.h 提取首块注释落盘
        tnt_h = load(self, os.path.join(self.source_folder, "tnt.h"))
        notice = tnt_h.split("*/", 1)[0] + "*/\n"
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"),
             notice)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "libtnt")
        self.cpp_info.set_property("cmake_target_name", "libtnt::libtnt")
