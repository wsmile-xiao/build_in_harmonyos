#!/usr/bin/env python3
"""Conan recipe for cppnumericalsolvers 2.0.0 (PatWie/CppNumericalSolvers).

header-only C++17 非线性优化求解器库（L-BFGS/BFGS/Newton/Trust-Region/
Nelder-Mead/Augmented-Lagrangian 等），include/cppoptlib 下全部模板实现，
依赖 Eigen。上游提供 Bazel + CMake 双构建（CMakeLists 仅注册
verify/cstep_test，Bazel BUILD 完整注册 5 个测试入口）。

版本说明：2.0.0 是上游正式 tag（v2.0.0），官方 archive URL 见
conandata.yml（github.com 官方源，CI 自动加镜像 fallback）。

OHOS 适配要点：
- header-only：package_id clear，直接拷 include/cppoptlib。
- 上游测试（src/test 下 5 个文件，源码声明 64 个独立用例：
  verify.cc 17 + cstep_test.cc 7 + hager_zhang_test.cc 4 +
  trust_region_newton_test.cc 9 + augmented_lagrangian_test.cc 27）：
  build() 内用 Conan gtest/1.17.0 直接编译实跑全部 5 个入口
  （绕过 Bazel 联网），include 根 = 仓库根（"include/cppoptlib/..."）。
- 2.0.0 API 为 cppoptlib::function::FunctionXd<F> /
  cppoptlib::solver::Lbfgs<F>::Minimize（与 1.0.0 的 Problem/BfgsSolver API 不同）。
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os


class CppNumericalSolversConan(ConanFile):
    name = "cppnumericalsolvers"
    version = "2.0.0"
    description = "Header-only C++17 non-linear optimization solvers (L-BFGS/Newton/Trust-Region/...)"
    license = "MIT"
    homepage = "https://github.com/PatWie/CppNumericalSolvers"
    url = ""  # CI fills this
    topics = ("optimization", "solver", "lbfgs", "header-only")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("eigen/3.4.1", transitive_headers=True)
        # 上游 5 个测试入口用 gtest（版本沿用已验证的 gtest 1.17.0）
        self.test_requires("gtest/1.17.0#ab1bc3bf51522490eef07a83c2dbd203")

    def package_id(self):
        self.info.clear()

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        src = self.source_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        eigen_inc = " ".join("-I" + p for p in self.dependencies["eigen"].cpp_info.includedirs)
        gt = self.dependencies["gtest"].cpp_info
        gt_inc = " ".join("-I" + p for p in gt.includedirs)
        gt_lib = gt.libdirs[0]
        # 上游测试以仓库根为 include 根（"include/cppoptlib/..."）
        tests = [
            ("verify", False),
            ("cstep_test", True),
            ("hager_zhang_test", True),
            ("trust_region_newton_test", False),
            ("augmented_lagrangian_test", False),
        ]
        for name, need_main in tests:
            extra = "-lgtest_main" if need_main else ""
            self.run(
                f"{cxx} -std=c++17 -O1 -I{src} -I{src}/include {eigen_inc} {gt_inc} "
                f"{os.path.join(src, 'src', 'test', name + '.cc')} "
                f"-L{gt_lib} -lgtest {extra} -pthread -o {name}",
                cwd=self.build_folder,
            )
            # 层1：上游 gtest 套件实跑（64 用例 = 17+7+4+9+27）
            self.run(f"./{name}", cwd=self.build_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*", src=os.path.join(self.source_folder, "include", "cppoptlib"),
             dst=os.path.join(self.package_folder, "include", "cppoptlib"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
