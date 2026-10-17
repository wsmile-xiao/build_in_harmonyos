#!/usr/bin/env python3
"""Conan recipe for cppnumericalsolvers 1.0.0 (PatWie/CppNumericalSolvers).

header-only C++ 非线性优化求解器库（BFGS/L-BFGS/CMA-ES/Nelder-Mead 等），
include/cppoptlib 下全部模板实现，依赖 Eigen。上游只提供 Bazel 构建
（WORKSPACE 里联网拉 gtest/eigen），无 CMake/预生成 configure。

版本说明：上游 git 仓无 v1.0.0 标签（只有 v1.0.0alpha1/alpha2、v2.0.0），
1.0.0 源码取自 Debian orig tarball（cppnumericalsolvers_1.0.0.orig.tar.gz，
Debian sid 收录版本），sha256 锁定于 conandata.yml。

OHOS 适配要点：
- header-only：package_id clear，直接拷 include/cppoptlib。
- 上游测试 src/test/verify.cpp（gtest，16 TEST + 23 TYPED_TEST = 39 个用例
  定义，typed 双精度实例化后 78 实例）：build() 内用 Conan gtest/1.17.0 直接
  编译实跑（绕过 Bazel 联网）。include 路径按仓库根（"include/cppoptlib/..."）。
- benchmark.cpp 是性能基准且 include 写死 "../../gtest/..." bazel 相对路径，
  非功能测试，不纳入（如实上报）。
"""
from conan import ConanFile
from conan.tools.files import copy, get
import os


class CppNumericalSolversConan(ConanFile):
    name = "cppnumericalsolvers"
    version = "1.0.0"
    description = "Header-only C++17 non-linear optimization solvers (BFGS/L-BFGS/CMA-ES/...)"
    license = "MIT"
    homepage = "https://github.com/PatWie/CppNumericalSolvers"
    url = ""  # CI fills this
    topics = ("optimization", "solver", "bfgs", "header-only")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("eigen/3.4.1", transitive_headers=True)
        # 上游 verify.cpp 用 gtest（版本沿用 atracdenc 已验证的 gtest 1.17.0）
        self.test_requires("gtest/1.17.0#ab1bc3bf51522490eef07a83c2dbd203")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        src = self.source_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        eigen_inc = " ".join("-I" + p for p in self.dependencies["eigen"].cpp_info.includedirs)
        gt = self.dependencies["gtest"].cpp_info
        gt_inc = " ".join("-I" + p for p in gt.includedirs)
        gt_lib = gt.libdirs[0]
        # verify.cpp 以 "include/cppoptlib/..." 相对仓库根 include
        self.run(
            f"{cxx} -std=c++17 -O1 -I{src} {eigen_inc} {gt_inc} "
            f"{os.path.join(src, 'src', 'test', 'verify.cpp')} "
            f"-L{gt_lib} -lgtest -pthread -o verify",
            cwd=self.build_folder,
        )
        # 层1：上游 gtest 套件实跑（16 TEST + 23 TYPED_TEST×2 类型 = 78 实例）
        self.run("./verify", cwd=self.build_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*", src=os.path.join(self.source_folder, "include", "cppoptlib"),
             dst=os.path.join(self.package_folder, "include", "cppoptlib"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
