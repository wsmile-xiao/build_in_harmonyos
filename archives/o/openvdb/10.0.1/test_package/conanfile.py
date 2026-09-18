#!/usr/bin/env python3
"""Conan test_package for openvdb 10.0.1 — 消费测试验证库可用性。

用法: python3 test_openvdb.py <package_folder>
"""
from conan import ConanFile


class OpenvdbTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # 消费测试全在 test() 完成（test_openvdb.py 手动编译 consumer 链接
    # libopenvdb），本包无 CMakeLists.txt，故不声明 CMake 构建。

    def test(self):
        pkg_folder = self.dependencies["openvdb"].package_folder
        # openvdb 头依赖 tbb/boost/zlib——把依赖 include 路径传给
        # test_openvdb.py（consumer 编译需要 -I 依赖头）。
        # 依赖名直接取 recipe requires 的固定三项，不做
        # `for dep_name in self.dependencies` 迭代：不同 Conan 2
        # 小版本 Dependencies 迭代协议不一致（CI 版本抛
        # TypeError: argument of type 'int' is not iterable，
        # #6887 CI 33892），而按名索引 self.dependencies[name]
        # 在本地 2.29.1 与 CI 版本均可用（本方法首行已验证）。
        dep_flags = []
        for dep_name in ("tbb", "zlib", "boost"):
            try:
                dep = self.dependencies[dep_name]
            except KeyError:
                continue
            for inc in dep.cpp_info.includedirs:
                dep_flags.append("--include=%s" % inc)
            for libd in dep.cpp_info.libdirs:
                dep_flags.append("-L%s" % libd)
            for lib in dep.cpp_info.libs:
                dep_flags.append("-l%s" % lib)
        # consumer 编译链接是构建行为：必须用 conanbuild 环境（含 SDK
        # lld 依赖的系统库路径）。conanrun 环境下 CI worker 的 lld 启动
        # 即崩（libxml2.so.16 not found，#44637）——本地环境恰好完备而
        # CI 不行，故此前未暴露。
        self.run('python3 test_openvdb.py "%s" %s'
                 % (pkg_folder, " ".join(dep_flags)), env="conanbuild")
