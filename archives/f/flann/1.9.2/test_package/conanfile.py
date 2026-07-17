#!/usr/bin/env python3
"""Conan test_package — flann 1.9.2 (C++ nearest-neighbor library).

L1 test: 用 flann C++ API 在小点集上建 kd-tree 索引并执行 knn 搜索,
验证最近邻正确性 (数据点自身的最近邻是自身)。

flann 的 C++ API 是 header-only 模板, 且其 serialization.h 内联 #include <lz4.h>,
故消费者编译需 flann 头 + lz4 头, 链接需 flann_cpp + vendored lz4。这里直接用
clang++ 编译链接 (不走 CMakeDeps/find_package, 避开 conan 2.29.1 对带 soname 的
近空共享库的 find_library 缺陷), 运行期 .so 由 conanrun 的 LD_LIBRARY_PATH 解析。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class FlannTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["flann"]
        inc = os.path.join(dep.package_folder, "include")
        libdir = os.path.join(dep.package_folder, "lib")
        src = os.path.join(self.source_folder, "test_flann.cpp")
        # 用 profile 配置的编译器: 容器内是 hnp wrapper (带 --rtlib=compiler-rt
        # -fuse-ld=lld, 否则 musl 下链不到 libgcc/crtbegin), CI 上是 OHOS clang。
        cxx = "clang++"
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if compilers.get("cpp"):
            cxx = compilers["cpp"]
        # 编译+链接测试程序 (flann C++ 头模板 + flann_cpp 共享库 + vendored lz4)
        self.run(
            f'"{cxx}" -std=c++17 -stdlib=libc++ -fPIC'
            f' -I"{inc}" -L"{libdir}" "{src}"'
            " -lflann_cpp -llz4_vendored -o test_flann",
            env="conanrun",
        )
        # 运行 — 正确返回 0, 失败返回 1
        self.run("./test_flann", env="conanrun")
