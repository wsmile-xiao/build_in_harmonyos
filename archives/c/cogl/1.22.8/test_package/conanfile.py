#!/usr/bin/env python3
"""Conan test_package for cogl 1.22.8 — 消费测试 + 上游纯 CPU 测试子集。

test() 收集全部依赖包（glib/gobject/egl/gles2 等传递依赖）的
cpp_info.includedirs/libdirs 写入 COGL_TEST_DEP_INCLUDES /
COGL_TEST_DEP_LIBDIRS，由 test_cogl.py 编译链接 consumer 与
upstream_unit/ 纯 CPU 子集（3 用例）时使用（cogl.h 内部解析 glib
头，需 glib 的 include 路径；CONAN_CFLAGS 聚合环境变量在 Conan 2
依赖 cpp_info 而非 env，实测为空不可靠）。
"""
import os

from conan import ConanFile


class CoglTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["cogl"].package_folder
        # 收集全部依赖（含传递）的 include/lib 目录——consumer 编译
        # cogl.h 需解析 glib 头（含 glib-object.h 等组件头），运行需
        # glib 的 .so。两点版本无关性保证：
        # 1) 固定按名取，不做 `for dep_name in self.dependencies`
        #    迭代——CI 环境 Conan 2 小版本 Dependencies 迭代协议
        #    不一致（抛 TypeError: argument of type 'int' is not
        #    iterable，#6992 CI 34083，同 #6887 CI 33892）；按名
        #    索引 self.dependencies[name] 在本地 2.29.1 与 CI 均
        #    可用（本方法首行已验证）。名称 = cogl 直接 requires
        #    (glib/gles2/egl) + glib 传递依赖 (libffi/pcre2/zlib)，
        #    未安装/缺失名称兜底跳过（egl/gles2 常为跳过 binary）。
        # 2) 组件包（glib recipe 用 glib-2.0/gobject-2.0 等
        #    components）顶层 dep.cpp_info.includedirs 不含组件级
        #    include（include/glib-2.0、lib/glib-2.0/include）——
        #    consumer 编译会缺 glib-object.h。优先用
        #    cpp_info.aggregated_components() 聚合组件信息
        #    （include/lib/libs 全量），无该方法（旧版本）时回退
        #    顶层 cpp_info。
        dep_incs = []
        dep_libdirs = []
        for dep_name in ("glib", "gles2", "egl", "libffi", "pcre2", "zlib"):
            try:
                dep = self.dependencies[dep_name]
            except KeyError:
                continue
            try:
                agg = dep.cpp_info.aggregated_components()
                incs = list(agg.includedirs)
                libds = list(agg.libdirs)
            except Exception:
                incs = list(dep.cpp_info.includedirs)
                libds = list(dep.cpp_info.libdirs)
            for inc in incs:
                if inc not in dep_incs:
                    dep_incs.append(inc)
            for libd in libds:
                if libd not in dep_libdirs:
                    dep_libdirs.append(libd)
        os.environ["COGL_TEST_DEP_INCLUDES"] = " ".join(dep_incs)
        os.environ["COGL_TEST_DEP_LIBDIRS"] = " ".join(dep_libdirs)
        self.run('python3 test_cogl.py "%s"' % pkg_folder, env="conanrun")
