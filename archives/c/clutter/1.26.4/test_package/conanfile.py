#!/usr/bin/env python3
"""Conan test_package for clutter 1.26.4 — 消费者视角验证（R34）。

test() 收集全部依赖（含传递）的 cpp_info include/lib 目录，写入
CLUTTER_TEST_DEP_INCLUDES / CLUTTER_TEST_DEP_LIBDIRS 传给
test_clutter.py；后者编译并运行 consumer.c，consumer.c 实质调用
Clutter 的免显示 API（版本宏、颜色换算、单位换算、Actor 生命周期与
属性系统）。

为何不调用 clutter_init()：OHOS 无显示服务（无 X11/Wayland/DRM），
clutter_init() 会因无法建立任何后端而失败——属平台能力缺口，不是
库缺陷。测试改走免显示 API 子集，真实证明库被链接、加载并执行。
"""
import os

from conan import ConanFile


class ClutterTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["clutter"].package_folder
        # 按名索引依赖（不做 Dependencies 迭代——CI 环境 Conan 小版本
        # 迭代协议不一致，仓库历史 #6992/#6887 有实测记录）。组件包
        # （glib/cairo/pango 用 components）需 aggregated_components()
        # 才能拿到组件级 include（include/glib-2.0 等），无该方法时
        # 回退顶层 cpp_info。
        dep_incs = []
        dep_libdirs = []
        for dep_name in ("cogl", "glib", "cairo", "pango", "atk",
                         "json-glib", "gles2", "egl", "harfbuzz",
                         "fontconfig", "freetype", "fribidi", "libthai",
                         "pixman", "libpng", "zlib", "pcre2", "libffi"):
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
        os.environ["CLUTTER_TEST_DEP_INCLUDES"] = " ".join(dep_incs)
        os.environ["CLUTTER_TEST_DEP_LIBDIRS"] = " ".join(dep_libdirs)
        self.run('python3 test_clutter.py "%s"' % pkg_folder, env="conanrun")
